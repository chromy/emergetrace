
## Onetime setup

```
python3 -m venv .env
source .env/bin/activate
pip3 install requests
pip3 install pandas
pip3 install perfetto
```

## Download a batch of traces
```
python3 emergetrace.py download span_12345
```

## Run a SQL query accross all traces
```
python3 emergetrace.py batch span_12345 "INCLUDE PERFETTO MODULE slices.with_context; with target as (select utid, name, ts, dur from thread_slice where name like 'SomeSliceName%')
         select state, sum(thread_state.dur) from thread_state join target where thread_state.utid = target.utid and target.ts <= thread_state.ts and thread_state.ts + thread_state.dur <= target.ts + target.dur group by state;"
```



