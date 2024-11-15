#!/usr/bin/env python3
import sys
import os
import argparse
import json
import subprocess
import glob

RED = "\033[31m"
ENDC = "\033[m"

def eprint(*args, **kwargs):
  is_term = sys.stderr.isatty()
  if is_term:
    print(RED, end="", file=sys.stderr)
  print(*args, file=sys.stderr, **kwargs)
  if is_term:
    print(ENDC, end="", file=sys.stderr)

def fatal(*args, **kwargs):
  eprint(*args, **kwargs)
  exit(1)

try:
  import perfetto
  from perfetto.batch_trace_processor.api import BatchTraceProcessor
  import requests
except ModuleNotFoundError:
  fatal("Unable to import additional dependencies (perfetto, requests) ensure these are installed globally or the virtual env is activated. See README.md for details.")


def download_trace(ctx, span_id, iteration, out):
  headers = {}
  headers["X-API-Token"] = ctx.get_api_token()
  data = {}
  data["iteration"] = iteration
  data["spanId"] = span_id
  response = requests.post(f"https://api.emergetools.com/trace", data=json.dumps(data), headers=headers)

  result = json.loads(response.text)
  url = result["url"]
  subprocess.check_output(["curl", url, "--output", out])


def do_download(ctx):
  span_id = ctx.args.span_id
  out_directory = ctx.get_out_directory()
  for i in range(93):
    if i < 3:
      continue
    out_path = os.path.join(out_directory, f"trace_{i}.pftrace")
    if os.path.exists(out_path):
      print(f"Skipping downloading {i} as {out_path}, already exists.")
      continue
    download_trace(ctx, span_id, i, out_path)


def do_batch(ctx):
  sql = ctx.get_query()

  out_directory = ctx.get_out_directory()
  files = os.listdir(out_directory)
  paths = [os.path.join(out_directory, name) for name in files if os.path.isfile(name)]

  if not paths:
    eprint(f"No available traces in {out_directory}.")
    return 1

  with BatchTraceProcessor(paths) as btp:
    df = btp.query_and_flatten(sql)
    print(df)
    df.to_csv('data.csv', index=True)


class Context(object):
  def __init__(self, args):
    self.args = args

  def get_api_token(self):
    api_token = self.args.api_token
    if not api_token:
      fatal("No API token available. Set EMERGE_API_TOKEN env variable or pass --api-token. See https://docs.emergetools.com/docs/uploading-basics#obtain-an-api-key.")
    return api_token

  def get_query(self):
    if self.args.SQL:
      return " ".join(self.args.SQL)
    elif self.args.query_file:
      if not os.path.isfile(self.args.query_file):
        fatal(f"No such file '{self.args.query_file}' for --query-file.")
      with open(self.args.query_file) as f:
        return f.read()
    else:
      return None

  def get_out_directory(self):
    directory = self.args.traces
    if not os.path.exists(directory):
      os.makedirs(directory)
    return directory


def main():
  parser = argparse.ArgumentParser(
      prog='emergetrace',
      description='Batch analysis of Emergetools Android Perfomance tests.',
      epilog='')

  api_token_default = os.environ["EMERGE_API_TOKEN"]
  traces_default = os.path.abspath(os.path.join(os.path.expanduser("~"), "traces"))

  parser.add_argument('--api-token', help=f"Set the API token. Defaults to env[EMERGE_API_TOKEN]. See https://docs.emergetools.com/docs/uploading-basics#obtain-an-api-key. (default: '{api_token_default}')", default=api_token_default)
  parser.add_argument('--traces', help=f"Directory for downloaded traces. (default: '{traces_default}')", default=traces_default)

  subparsers = parser.add_subparsers()

  download_cmd = subparsers.add_parser("download", help="Download traces for a given spanId")
  download_cmd.add_argument("span_id", help="ID of a test span")
  download_cmd.set_defaults(func=do_download)

  batch_cmd = subparsers.add_parser("batch", help="")
  #batch_cmd.add_argument("regex", help="Regex for ")
  batch_cmd.add_argument("-q", "--query-file", help="path to a text file containing a SQL query to run")
  batch_cmd.add_argument("SQL", nargs="*", help="SQL query to run")
  batch_cmd.set_defaults(func=do_batch)

  args = parser.parse_args()

  if args.func == do_batch and not args.SQL and not args.query_file:
    eprint("Error: Must pass SQL query either via SQL or -q/--query-file.")
    batch_cmd.print_help(sys.stderr)
    return 1

  ctx = Context(args)

  try:
    f = args.func
  except AttributeError:
    parser.print_help(sys.stderr)
    return 1
  else:
    return f(ctx)

if __name__ == "__main__":
  sys.exit(main())
