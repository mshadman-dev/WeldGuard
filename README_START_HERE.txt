WELDGUARD v0.6.0 — LOCAL MULTI-BAY DEMONSTRATION PROTOTYPE

WHAT IS INCLUDED
- app.py: Streamlit application with three simulated welding bays.
- requirements.txt: Python packages needed by the app.
- CAD/WeldGuard_Concept_Model.scad: editable OpenSCAD concept model.
- CAD/README_CAD.txt: instructions for opening the CAD model.

RUN ON macOS
1. Install Python 3 and OpenSCAD if not already installed.
2. Open Terminal and change directory into this extracted folder.
3. Create an isolated environment:
   python3 -m venv .venv
4. Activate it:
   source .venv/bin/activate
5. Install dependencies:
   python -m pip install -r requirements.txt
6. Start WeldGuard:
   streamlit run app.py
7. Open the local address printed by Streamlit (normally http://localhost:8501).

FEATURES
- Central overview of Bay 01, Bay 02 and Bay 03.
- Independent simulated PM2.5 readings and configurable thresholds per bay.
- Demonstration scenario button to populate all three bays with different conditions.
- Automatic/manual simulated fan command.
- Workstation concept visualisation.
- Bay-filtered alerts with acknowledgement and resolution tracking.
- Persistent SQLite readings, events and settings in weldguard.db beside app.py.
- CSV exports and generated PDF session report.
- Downloadable SQLite backup and guarded history-clearing control.
- Editable OpenSCAD concept model in CAD folder.

IMPORTANT LIMITATIONS
This is a laptop-only simulation and concept visualisation. It does not connect to an ESP32,
PMS5003, real fan, alarm or physical extraction system. Readings and airflow/fan states are
simulated. PM1.0 and PM10 are illustrative values derived from the PM2.5 simulation. The
particulate concept does not identify chemical composition or toxicity. Demo thresholds are
not occupational exposure limits. This is not a workplace safety monitor, extraction design,
or safety certification. Do not use it to make real worker-safety decisions.

DATA
The SQLite database is created automatically in the same folder as app.py. Back it up using
System Settings > Local data backup before moving or replacing the project. Clearing history
removes readings and events but preserves bay settings.

VERSION
0.6.0 — Multi-bay demo scenario, local SQLite persistence, event workflows, reports,
backup controls and editable CAD concept. Syntax-checked in the build environment; a full
Streamlit browser run still needs to be launched on the target Mac.
