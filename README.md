# Emergetrace

Batch analysis for traces from Emergetools performance runs.

## Onetime setup

Cone the repo:
```
git clone https://github.com/chromy/emergetrace.git
cd emergetrace
```

Install Python dependencies:
```
python3 -m venv .env
source .env/bin/activate
pip3 install -r requirements.txt
```

Export API token. You may want to add this to `.bashrc` / `.zshrc` etc.
See https://docs.emergetools.com/docs/uploading-basics#obtain-an-api-key
to get an API key.
```
export EMERGE_API_TOKEN=[Your API token]
```

## Download a batch of traces
```
./emergetrace download span_12345
```

## Run a SQL query across all traces
```
./emergetrace batch span_12345 "INCLUDE PERFETTO MODULE slices.with_context; with target as (select utid, name, ts, dur from thread_slice where name like 'SomeSliceName%')
         select state, sum(thread_state.dur) from thread_state join target where thread_state.utid = target.utid and target.ts <= thread_state.ts and thread_state.ts + thread_state.dur <= target.ts + target.dur group by state;"
```

  # python3 emergetrace.py batch span_bamh5XrbgTsh "INCLUDE PERFETTO MODULE slices.with_context; with target as (select utid, name, ts, dur from thread_slice where name like 'file_read%summary.json')
  # select state, sum(thread_state.dur) from thread_state join target where thread_state.utid = target.utid and target.ts <= thread_state.ts and thread_state.ts + thread_state.dur <= target.ts + target.dur group by state;"


