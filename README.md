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

## Show information about an upload
```
./emergetrace analysis 30d3ef42-a9c0-429a-acdb-1236f099dba8
```

## Download a batch of traces

All traces for a given upload:
```
./emergetrace download 30d3ef42-a9c0-429a-acdb-1236f099dba8
```

Only the traces for span 'span_1234' for an upload:
```
./emergetrace download 30d3ef42-a9c0-429a-acdb-1236f099dba8 --span-id span_1234
```

Only the traces for samples 42 and 45 for span 'span_1234' for an upload:
```
./emergetrace download 30d3ef42-a9c0-429a-acdb-1236f099dba8 --span-id span_1234 -s 42 45
```

## Run a SQL query across all traces
```
./emergetrace batch 'select count(*) from slice;'
```

Output the results to a .csv
```
./emergetrace batch --csv --out data.csv 'select count(*) from slice;'
```

Output the results as .json reading the query from a file:
```
./emergetrace batch --json -q bindApplication_by_thread_state.sql
```

