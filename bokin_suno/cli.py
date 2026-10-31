"""Command line entry point: `bokin-suno <command> ...`."""

import argparse
import json
import os
import sys

NOTES = {
    "clipped_input": "the song is clipped in places (distortion that mastering cannot undo)",
    "target_not_reached": "the target loudness was not reached: the limiter would have had "
                          "to squash the song too hard",
    "mp3_overs": "the MP3 encoder pushed peaks near 0 dBFS: use a lower ceiling (e.g. -1.5)",
}


def _add_master_options(p):
    from bokin_suno.master import PRESETS

    p.add_argument("--preset", default="streaming", choices=list(PRESETS),
                   help="starting point (default: streaming, -14 LUFS)")
    p.add_argument("--reference", help="a finished song to match (tone, width)")
    p.add_argument("--match", type=float, help="how far to match the reference, 0-1 (default 0.7)")
    p.add_argument("--match-loudness", action="store_true",
                   help="use the reference's loudness as the target")
    p.add_argument("--lufs", type=float, help="target loudness, e.g. -14")
    p.add_argument("--keep-loudness", action="store_true",
                   help="no loudness target: only keep peaks under the ceiling")
    p.add_argument("--ceiling", type=float, help="true-peak ceiling in dBTP (default -1)")
    for name, what in (("shimmer", "remove Suno shimmer/metallic grain"),
                       ("dehiss", "remove hiss"), ("deess", "tame harsh S sounds"),
                       ("dewhine", "remove steady whines")):
        p.add_argument(f"--{name}", type=float, metavar="0-1", help=what)
    for name, what in (("bass", "low shelf at 100 Hz"), ("body", "wide bell at 180 Hz (fuller)"),
                       ("mud", "bell at 300 Hz"), ("presence", "wide bell at 2.5 kHz (clearer)"),
                       ("harsh", "bell at 3.5 kHz"), ("air", "high shelf at 10 kHz")):
        p.add_argument(f"--{name}", type=float, metavar="DB", help=what)
    p.add_argument("--warmth", type=float, metavar="0-1", help="gentle saturation of the low mids")
    p.add_argument("--density", type=float, metavar="0-1",
                   help="parallel compression: quiet details come up")
    p.add_argument("--glue", type=float, metavar="0-1", help="bus compression")
    p.add_argument("--mono-bass", type=float, metavar="HZ", help="mono below this (0: off)")
    p.add_argument("--width", type=float, metavar="DB", help="stereo width change above the bass")
    p.add_argument("--lowcut", type=float, metavar="HZ", help="rumble filter (0: off)")
    p.add_argument("--sr", type=int, help="output sample rate, e.g. 44100")
    p.add_argument("--format", choices=["wav", "flac", "mp3"])
    p.add_argument("--bits", type=int, choices=[16, 24, 32])
    p.add_argument("--no-removed", action="store_true",
                   help="do not write <name>_removed.wav (what cleaning took out)")


def settings_from_args(args):
    from bokin_suno.master import preset

    overrides = {}
    for key, value in (("target_lufs", args.lufs), ("ceiling_db", args.ceiling),
                       ("match", args.match), ("glue", args.glue),
                       ("warmth", args.warmth), ("density", args.density),
                       ("mono_bass_hz", args.mono_bass), ("width_db", args.width),
                       ("lowcut_hz", args.lowcut), ("sample_rate", args.sr),
                       ("format", args.format), ("bits", args.bits)):
        if value is not None:
            overrides[key] = value
    if args.keep_loudness:
        overrides["target_lufs"] = None
    if args.match_loudness:
        overrides["match_loudness"] = True
    if args.no_removed:
        overrides["write_removed"] = False
    clean = {k: getattr(args, k) for k in ("shimmer", "dehiss", "deess", "dewhine")
             if getattr(args, k) is not None}
    eq = {k: getattr(args, k) for k in ("bass", "body", "mud", "presence", "harsh", "air")
          if getattr(args, k) is not None}
    return preset(args.preset, clean=clean, eq=eq, **overrides)


def _line(m: dict) -> str:
    lra = "-" if m["lra"] is None else f"{m['lra']}"
    return f"{m['lufs']:.1f} LUFS, {m['true_peak_db']:.1f} dBTP, LRA {lra}"


def cmd_master(args) -> int:
    from bokin_suno.audio_io import audio_files
    from bokin_suno.master import master_file, style_of

    settings = settings_from_args(args)
    label = style_of(settings, args.preset)["label"]  # (in the master's file name)
    settings.check()  # bad settings fail once, not once per song
    require_licence()
    files = audio_files(args.songs)
    if not files:
        print("error: no audio files", file=sys.stderr)
        return 2
    failed = 0
    for i, path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {path.name}", flush=True)
        try:
            result = master_file(path, args.out, settings, args.reference, label=label)
        except Exception as err:  # keep going with the other songs
            print(f"  x {err}", file=sys.stderr)
            failed += 1
            continue
        r = result.report
        print(f"  in : {_line(r['input'])}")
        print(f"  out: {_line(r['output'])}")
        for note in r["notes"]:
            print(f"  ! {NOTES.get(note, note)}")
        print(f"  -> {result.output}")
    return 1 if failed else 0


def cmd_analyze(args) -> int:
    from bokin_suno import audio_io
    from bokin_suno.analysis import measure

    for path in audio_io.audio_files(args.songs):
        x, sr = audio_io.load(path)
        m = measure(x, sr)
        print(json.dumps({"file": path.name, **m}) if args.json else f"{path.name}: {_line(m)}")
    return 0


def cmd_app(args) -> int:
    from bokin_suno import desktop

    if args.no_browser:
        os.environ["BOKIN_NO_BROWSER"] = "1"
    return desktop.serve(out_dir=args.out, idle_exit=False)


def require_licence() -> None:
    """The command line masters only where the app is activated, like the window."""
    from bokin_suno import licensing

    if licensing.licensed():
        return
    state = licensing.view()
    if not state["licensed"]:
        raise SystemExit(f"{state['message']}\nMachine code (send it to the seller): {state['machine']}\n"
                         "Then paste the key in the app's activation screen (bokin-suno app).")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="bokin-suno",
                                     description="Clean up and master songs made with Suno AI.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("master", help="master songs (files or folders)")
    p.add_argument("songs", nargs="+")
    p.add_argument("--out", default="outputs", help="output folder (default: outputs)")
    _add_master_options(p)
    p.set_defaults(func=cmd_master)

    p = sub.add_parser("analyze", help="loudness, true peak and LRA of songs")
    p.add_argument("songs", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("app", help="open the app (in a browser window)")
    p.add_argument("--no-browser", action="store_true", help="only start the server")
    p.add_argument("--out", help="where results go (default: Music/Bokin Suno Master)")
    p.set_defaults(func=cmd_app)

    args = parser.parse_args(argv)
    try:
        sys.exit(args.func(args))
    except (ValueError, RuntimeError) as err:
        print(f"error: {err}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
