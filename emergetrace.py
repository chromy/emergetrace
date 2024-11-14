import sys
import os
import perfetto
import argparse
import json
import requests
import subprocess

from perfetto.batch_trace_processor.api import BatchTraceProcessor

API_TOKEN = os.environ["EMERGE_API_TOKEN"]

def download_trace(span_id, iteration, out):
  headers = {}
  headers["X-API-Token"] = API_TOKEN
  data = {}
  data["iteration"] = iteration
  data["spanId"] = span_id
  response = requests.post(f"https://api.emergetools.com/trace", data=json.dumps(data), headers=headers)

  result = json.loads(response.text)
  url = result["url"]
  subprocess.check_output(["curl", url, "--output", out])

def do_download(args):
  out_directory = "traces"
  for i in range(93):
    if i < 3:
      continue
    out_path = os.path.join(out_directory, f"trace_{iteration}.perfetto-trace")
    if os.path.exists(out_path):
      print(f"Skipping {i}")
      continue
    download_trace(span_id, i, out_path)

def main():
  parser = argparse.ArgumentParser(
      prog='emergetrace',
      description='',
      epilog='')

  subparsers = parser.add_subparsers()

  download_cmd = subparsers.add_parser('download', help='Download traces for a given spanId')
  download_cmd.add_argument('span_id', help='ID of a test span')
  download_cmd.set_defaults(func=do_download)

  args = parser.parse_args()

  try:
    f = args.func
  except AttributeError:
    parser.print_help(sys.stderr)
    return 1
  else:
    return f(args)

if __name__ == "__main__":
  sys.exit(main())
