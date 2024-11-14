import sys
import os
import perfetto
import argparse
import json
import requests
import subprocess
import glob

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
  span_id = args.span_id
  out_directory = "traces"
  for i in range(93):
    if i < 3:
      continue
    out_path = os.path.join(out_directory, f"trace_{i}.perfetto-trace")
    if os.path.exists(out_path):
      print(f"Skipping {i}")
      continue
    download_trace(span_id, i, out_path)

def do_batch(args):
  span_id = args.span_id
  sql = args.sql
  out_directory = "traces"
  files = glob.glob('traces/*.perfetto-trace')
  with BatchTraceProcessor(files) as btp:
    df = btp.query_and_flatten(sql)
    print(df)
    df.to_csv('data.csv', index=True)

def main():
  parser = argparse.ArgumentParser(
      prog='emergetrace',
      description='',
      epilog='')

  subparsers = parser.add_subparsers()

  download_cmd = subparsers.add_parser('download', help='Download traces for a given spanId')
  download_cmd.add_argument('span_id', help='ID of a test span')
  download_cmd.set_defaults(func=do_download)

  batch_cmd = subparsers.add_parser('batch', help='')
  batch_cmd.add_argument('span_id', help='ID of a test span')
  batch_cmd.add_argument('sql', help='ID of a test span')
  batch_cmd.set_defaults(func=do_batch)

  args = parser.parse_args()

  # python3 emergetrace.py batch span_bamh5XrbgTsh "INCLUDE PERFETTO MODULE slices.with_context; with target as (select utid, name, ts, dur from thread_slice where name like 'file_read%summary.json')
  # select state, sum(thread_state.dur) from thread_state join target where thread_state.utid = target.utid and target.ts <= thread_state.ts and thread_state.ts + thread_state.dur <= target.ts + target.dur group by state;"

  try:
    f = args.func
  except AttributeError:
    parser.print_help(sys.stderr)
    return 1
  else:
    return f(args)

if __name__ == "__main__":
  sys.exit(main())
