INCLUDE PERFETTO MODULE slices.with_context;
with
  target as (select utid, name, ts, max(dur) as dur from thread_slice where name like 'bindApplication')
  select
    state,
    sum(thread_state.dur)
  from thread_state
  join target
  where
    thread_state.utid = target.utid and
    target.ts <= thread_state.ts and
    thread_state.ts + thread_state.dur <= target.ts + target.dur
  group by state;
