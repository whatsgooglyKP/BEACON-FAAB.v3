"""Beacon evaluation + telemetry lab.

Everything in this package sits *beside* the Beacon app. It reads the same
cleaned, public, aggregate tract data the app ships with
(``app/public/data/*.json``) and never writes into ``app/`` or the pipeline.
"""
