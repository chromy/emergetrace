#!/usr/bin/env python3
import sys
import os
import argparse
import json
import subprocess
import re

RED = "\033[31m"
ENDC = "\033[m"
BLUE = "\033[0;34m"

def eprint(*args, **kwargs):
  is_term = sys.stderr.isatty()
  if is_term:
    print(RED, end="", file=sys.stderr)
  print(*args, file=sys.stderr, **kwargs)
  if is_term:
    print(ENDC, end="", file=sys.stderr)
  sys.stderr.flush()

def iprint(*args, **kwargs):
  is_term = sys.stderr.isatty()
  if is_term:
    print(BLUE, end="", file=sys.stderr)
  print(*args, file=sys.stderr, **kwargs)
  if is_term:
    print(ENDC, end="", file=sys.stderr)
  sys.stderr.flush()

def fatal(*args, **kwargs):
  eprint(*args, **kwargs)
  exit(1)

try:
  import perfetto
  from perfetto.batch_trace_processor.api import BatchTraceProcessor
  from perfetto.trace_uri_resolver.resolver import TraceUriResolver
  import requests
except ModuleNotFoundError:
  fatal("Unable to import additional dependencies (perfetto, requests) ensure these are installed globally or the virtual env is activated. See README.md for details.")


class TraceResolver(TraceUriResolver):
  def __init__(self, paths):
    self.paths = paths

  def resolve(self):
    results = []
    for path in self.paths:
      results.append(TraceUriResolver.Result(trace=path, metadata={'path': path}))
    return results


def get_analysis(ctx):
  headers = {}
  headers["X-API-Token"] = ctx.get_api_token()
  params = {}
  params["emergeId"] = ctx.args.EMERGE_ID
  response = requests.get(f"https://api.emergetools.com/analysis", params=params, headers=headers)
  if not response.ok:
    fatal(f"{response.status_code} while requesting {response.url} due to '{response.reason}'")
  return json.loads(response.text)


def download_trace(ctx, span_id, iteration, out):
  headers = {}
  headers["X-API-Token"] = ctx.get_api_token()
  data = {}
  data["iteration"] = iteration
  data["spanId"] = span_id
  response = requests.post(f"https://api.emergetools.com/trace", data=json.dumps(data), headers=headers)
  if not response.ok:
    fatal(f"{response.status_code} while requesting {response.url} due to '{response.reason}'")

  result = json.loads(response.text)
  url = result["url"]
  subprocess.check_output(["curl", url, "--output", out])


def do_show(ctx):
  analysis = get_analysis(ctx)
  json.dump(analysis, sys.stdout, indent=4)


def do_download(ctx):
  analysis = get_analysis(ctx)

  trace_directory = ctx.get_trace_directory()

  for test in analysis["performanceTests"]:
    span_id = test["id"]
    name = test["name"]

    if ctx.args.span_id and not span_id in ctx.args.span_id:
      ctx.i(f"Skipping {span_id} ({name})")
      continue

    base_iterations = len(test["buildDetails"]["baseBuildDetails"]["samples"])
    head_iterations = len(test["buildDetails"]["currentBuildDetails"]["samples"])

    ctx.i(f"Downloading {span_id} ({name}) iterations 3..{base_iterations+head_iterations+3}")

    for i in range(3, base_iterations+head_iterations+3):
      trace_path = os.path.join(trace_directory, f"trace_{span_id}_{i}.pftrace")
      if ctx.args.sample and not i in ctx.args.sample:
        ctx.i(f"Skipping {span_id} ({name}) sample {i}")
        continue

      if os.path.exists(trace_path):
        iprint(f"Skipping downloading {i} as {trace_path}, already exists.")

      ctx.i(f"Downloading {span_id} ({name}) sample {i}")
      download_trace(ctx, span_id, i, trace_path)


def do_batch(ctx):
  sql = ctx.get_query()

  trace_directory = ctx.get_trace_directory()
  all_files = os.listdir(trace_directory)

  if ctx.args.regex:
    files = [file for file in all_files if re.match(ctx.args.regex, file)]
  else:
    files = all_files

  all_paths = [os.path.join(trace_directory, name) for name in files]
  paths = [path for path in all_paths if os.path.isfile(path)]

  if paths:
    iprint(f"Running query on {len(paths)} of {len(all_files)} available traces.")
  elif ctx.args.regex:
    iprint(f"No matching traces in {trace_directory} ('{ctx.args.regex}').")
    return 1
  else:
    iprint(f"No available traces in {trace_directory}.")
    return 1

  resolver = TraceResolver(paths)

  out = ctx.get_out()
  with BatchTraceProcessor(resolver) as btp:
    df = btp.query_and_flatten(sql)

    if ctx.args.csv:
      df.to_csv(out)
    elif ctx.args.json:
      df.to_json(out, orient="records")
    elif ctx.args.tsv:
      df.to_csv(out, sep="\t")
    else:
      df.to_csv(out, sep="\t")


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

  def get_trace_directory(self):
    directory = self.args.traces
    if not os.path.exists(directory):
      os.makedirs(directory)
    return directory

  def get_out(self):
    path = self.args.out
    if path == "-":
      return sys.stdout
    else:
      return open(path, "w")

  def i(self, *args, **kwargs):
    if self.args.verbose:
      iprint(*args, **kwargs)


def main():
  parser = argparse.ArgumentParser(
      prog='emergetrace',
      description='Batch analysis of Emergetools Android Perfomance tests.',
      epilog='')

  api_token_default = os.environ["EMERGE_API_TOKEN"]
  traces_default = os.path.abspath(os.path.join(os.path.expanduser("~"), "traces"))
  out_default = "-"

  parser.add_argument('--api-token', help=f"Set the API token. Defaults to env[EMERGE_API_TOKEN]. See https://docs.emergetools.com/docs/uploading-basics#obtain-an-api-key. (default: '{api_token_default}')", default=api_token_default)
  parser.add_argument('--traces', help=f"Directory for downloaded traces. (default: '{traces_default}')", default=traces_default)
  parser.add_argument('--verbose', action="store_true", help="Output additional logging.")

  subparsers = parser.add_subparsers()

  show_cmd = subparsers.add_parser("show", help="Show information about an upload")
  show_cmd.add_argument("EMERGE_ID", help="id of a given upload (looks like dbacbe2a-4446-42c7-b48c-671748e71429 you can find this in the URL bar on most pages)")
  show_cmd.set_defaults(func=do_show)

  download_cmd = subparsers.add_parser("download", help="Download traces for an upload")
  download_cmd.add_argument("EMERGE_ID", help="id of a given upload (looks like dbacbe2a-4446-42c7-b48c-671748e71429 you can find this in the URL bar on most pages)")
  download_cmd.add_argument("--span-id", nargs="+", help="download only the given span ids")
  download_cmd.add_argument("-s", "--sample", nargs="*", type=int, help="download only the given samples")
  download_cmd.set_defaults(func=do_download)

  batch_cmd = subparsers.add_parser("batch", help="Run SQL query over many traces")
  batch_cmd.add_argument("--regex", help="If set filter traces to those matching regex")
  batch_cmd.add_argument("-q", "--query-file", help="path to a text file containing a SQL query to run")
  batch_cmd.add_argument("--csv", action="store_true", help="output query results as CSV")
  batch_cmd.add_argument("--tsv", action="store_true", help="output query results as TSV")
  batch_cmd.add_argument("--json", action="store_true", help="output results as Json")
  batch_cmd.add_argument("--out", help="output path (default: '{out_default}')", default=out_default)
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
