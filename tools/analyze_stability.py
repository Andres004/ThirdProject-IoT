"""RNF1: stability of the smart object, read from a serial monitor log.

The log is the one saved by `pio device monitor` (log2file filter) in logs/. The script
measures how long the smart object ran, how many times it restarted (a BOOT after the first
line), how many connections it lost, and the longest pause between two distance PUBs: a
pause much longer than the sample period means loop() was blocked.

With --stop-at-first-drop only the part before the first WIFI_LOST or MQTT_LOST is used,
so drops provoked on purpose for RNF5 later in the same log do not count here.

PASS needs at least MIN_STABILITY_DURATION_S, no restart and no pause over MAX_PUBLISH_GAP_MS.
"""

import argparse
from pathlib import Path

import tools_config as cfg
from report import Report
from serial_log import LogEvent, read_events, split_by_boot


def cut_at_first_drop(events: list[LogEvent]) -> list[LogEvent]:
    """Return the events before the first WIFI_LOST or MQTT_LOST."""
    for index, event in enumerate(events):
        if event.name in (cfg.EVENT_WIFI_LOST, cfg.EVENT_MQTT_LOST):
            return events[:index]
    return events


def analyze(report: Report, events: list[LogEvent]) -> None:
    """Write the stability figures of `events` and the final verdict line."""
    runs = split_by_boot(events)
    restarts = max(len(runs) - 1, 0)
    longest_run_s = max(((run[-1].t_ms - run[0].t_ms) / cfg.MS_PER_S for run in runs),
                        default=0.0)
    wifi_lost = sum(1 for e in events if e.name == cfg.EVENT_WIFI_LOST)
    mqtt_lost = sum(1 for e in events if e.name == cfg.EVENT_MQTT_LOST)

    publications = 0
    seq_gaps = 0
    max_gap_ms = 0
    for run in runs:
        pubs = [(e.t_ms, seq) for e in run if (seq := e.distance_seq()) is not None]
        publications += len(pubs)
        for (prev_ms, prev_seq), (cur_ms, cur_seq) in zip(pubs, pubs[1:]):
            max_gap_ms = max(max_gap_ms, cur_ms - prev_ms)
            seq_gaps += max(cur_seq - prev_seq - 1, 0)

    report.line(f"Events={len(events)} distance_pubs={publications} restarts={restarts} "
                f"wifi_lost={wifi_lost} mqtt_lost={mqtt_lost} seq_gaps={seq_gaps}")
    report.line(f"Longest run without restart: {longest_run_s:.{cfg.TIME_DECIMALS}f} s; "
                f"longest pause between distance PUBs: {max_gap_ms} ms "
                f"(limit {cfg.MAX_PUBLISH_GAP_MS:g} ms)")

    if publications < cfg.MIN_LOG_PUBLICATIONS:
        report.line(final_line(longest_run_s, restarts, max_gap_ms, cfg.RESULT_NOT_ENOUGH_DATA))
        return
    passed = (longest_run_s >= cfg.MIN_STABILITY_DURATION_S and restarts == 0
              and max_gap_ms <= cfg.MAX_PUBLISH_GAP_MS)
    report.line(final_line(longest_run_s, restarts, max_gap_ms,
                           cfg.RESULT_PASS if passed else cfg.RESULT_FAIL))


def final_line(duration_s: float, restarts: int, max_gap_ms: int, result: str) -> str:
    """Build the one-line verdict for RNF1."""
    return (f"RNF1 stability duration={duration_s:.{cfg.TIME_DECIMALS}f} s "
            f"restarts={restarts} max_pub_gap={max_gap_ms} ms "
            f"limit>={cfg.MIN_STABILITY_DURATION_S:g} s -> {result}")


def main() -> None:
    """Parse the arguments, analyze the log and optionally save the report."""
    parser = argparse.ArgumentParser(
        description="RNF1: duration, restarts and freezes in a serial monitor log.")
    parser.add_argument("log", type=Path, help="serial monitor log of the smart object")
    parser.add_argument("--stop-at-first-drop", action="store_true",
                        help="only use the part before the first WIFI_LOST or MQTT_LOST")
    parser.add_argument("--output", type=Path, help="also save the report to this file")
    args = parser.parse_args()

    report = Report("RNF1 stability analysis")
    report.line(f"Log: {args.log.name}" + (" (until the first drop)"
                                           if args.stop_at_first_drop else ""))
    events = read_events(args.log)
    if args.stop_at_first_drop:
        events = cut_at_first_drop(events)
    analyze(report, events)
    if args.output is not None:
        report.save(args.output)


if __name__ == "__main__":
    main()
