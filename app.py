
import random
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# -------------------- PAGE SETTINGS --------------------

st.set_page_config(
    page_title="Network Device Health Monitoring",
    page_icon="🖧",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "network_devices.csv"

CPU_DEFAULT = 80
MEMORY_DEFAULT = 85

DEVICES = [
    {"Device": "Router-01", "Type": "Router", "IP Address": "192.168.1.1"},
    {"Device": "Router-02", "Type": "Router", "IP Address": "192.168.1.2"},
    {"Device": "Switch-01", "Type": "Switch", "IP Address": "192.168.1.10"},
    {"Device": "Switch-02", "Type": "Switch", "IP Address": "192.168.1.11"},
    {"Device": "Server-01", "Type": "Server", "IP Address": "192.168.1.20"},
    {"Device": "Server-02", "Type": "Server", "IP Address": "192.168.1.21"},
    {"Device": "Server-03", "Type": "Server", "IP Address": "192.168.1.22"},
]

COLUMNS = [
    "Snapshot", "Timestamp", "Device", "Type", "IP Address",
    "Status", "CPU Usage (%)", "Memory Usage (%)", "Alert",
]


# -------------------- MONITORING LOGIC --------------------

def collect_data(scenario, cpu_limit, memory_limit, snapshot):
    """Create one monitoring snapshot using simulated device readings."""
    rows = []

    for device in DEVICES:
        online = random.random() > 0.10
        cpu = random.randint(5, 75) if online else 0
        memory = random.randint(10, 75) if online else 0

        # Repeatable test scenarios for demonstrations
        if scenario == "Normal Operation":
            online = True
            cpu = random.randint(15, min(cpu_limit - 1, 65))
            memory = random.randint(20, min(memory_limit - 1, 70))

        elif scenario == "Router Offline":
            if device["Device"] == "Router-01":
                online, cpu, memory = False, 0, 0

        elif scenario == "High CPU Usage":
            if device["Device"] == "Server-01":
                online, cpu, memory = True, min(100, cpu_limit + 10), 45

        elif scenario == "High Memory Usage":
            if device["Device"] == "Server-02":
                online, cpu, memory = True, 40, min(100, memory_limit + 10)

        elif scenario == "Multiple Faults":
            if device["Device"] == "Router-01":
                online, cpu, memory = False, 0, 0
            elif device["Device"] == "Server-01":
                online, cpu, memory = True, min(100, cpu_limit + 10), 45
            elif device["Device"] == "Switch-01":
                online, cpu, memory = True, 35, min(100, memory_limit + 10)

        # Determine health status
        if not online:
            status = "OFFLINE"
            alert = "Device unreachable"
        elif cpu >= cpu_limit and memory >= memory_limit:
            status = "CRITICAL"
            alert = "High CPU and memory usage"
        elif cpu >= cpu_limit:
            status = "WARNING"
            alert = "High CPU usage"
        elif memory >= memory_limit:
            status = "WARNING"
            alert = "High memory usage"
        else:
            status = "ONLINE"
            alert = "No issue detected"

        rows.append({
            "Snapshot": snapshot,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **device,
            "Status": status,
            "CPU Usage (%)": cpu,
            "Memory Usage (%)": memory,
            "Alert": alert,
        })

    return pd.DataFrame(rows, columns=COLUMNS)


def save_snapshot(new_data):
    """Append new readings to persistent CSV history."""
    if HISTORY_FILE.exists():
        try:
            old_data = pd.read_csv(HISTORY_FILE)
            old_data = old_data.reindex(columns=COLUMNS)
            combined = pd.concat([old_data, new_data], ignore_index=True)
        except (ValueError, pd.errors.ParserError, OSError):
            combined = new_data.copy()
    else:
        combined = new_data.copy()

    combined.to_csv(HISTORY_FILE, index=False)
    return combined


def load_history():
    """Read saved monitoring records if available."""
    if HISTORY_FILE.exists():
        try:
            data = pd.read_csv(HISTORY_FILE)
            if all(column in data.columns for column in COLUMNS):
                return data[COLUMNS]
        except (ValueError, pd.errors.ParserError, OSError):
            pass
    return pd.DataFrame(columns=COLUMNS)


# -------------------- SIDEBAR --------------------

st.sidebar.title("⚙️ Monitoring Settings")

scenario = st.sidebar.selectbox(
    "Test Scenario",
    [
        "Normal Operation",
        "Random Simulation",
        "Router Offline",
        "High CPU Usage",
        "High Memory Usage",
        "Multiple Faults",
    ],
)

cpu_limit = st.sidebar.slider(
    "CPU warning threshold (%)", 50, 100, CPU_DEFAULT
)

memory_limit = st.sidebar.slider(
    "Memory warning threshold (%)", 50, 100, MEMORY_DEFAULT
)

st.sidebar.caption(
    "Test scenarios use simulated readings. "
    "They do not control physical network devices."
)

if st.sidebar.button("🗑️ Clear Monitoring History"):
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
    st.session_state.pop("history", None)
    st.session_state.pop("latest", None)
    st.rerun()


# -------------------- INITIALIZE AND REFRESH --------------------

if "history" not in st.session_state:
    st.session_state.history = load_history()

if "latest" not in st.session_state:
    saved = st.session_state.history
    if not saved.empty:
        latest_snapshot = saved["Snapshot"].max()
        st.session_state.latest = saved[
            saved["Snapshot"] == latest_snapshot
        ].copy()
    else:
        initial = collect_data(
            scenario, cpu_limit, memory_limit, snapshot=1
        )
        st.session_state.history = save_snapshot(initial)
        st.session_state.latest = initial

if st.button("🔄 Refresh Monitoring", type="primary"):
    history = st.session_state.history
    next_snapshot = (
        int(pd.to_numeric(history["Snapshot"], errors="coerce").max()) + 1
        if not history.empty else 1
    )

    new_data = collect_data(
        scenario, cpu_limit, memory_limit, next_snapshot
    )
    st.session_state.history = save_snapshot(new_data)
    st.session_state.latest = new_data
    st.rerun()


# -------------------- DASHBOARD --------------------

st.title("🖧 Network Device Health Monitoring System")
st.caption("Network Management System Mini-Project | Python + Streamlit")

st.info(
    f"Simulation mode | Scenario: {scenario} | "
    f"CPU threshold: {cpu_limit}% | "
    f"Memory threshold: {memory_limit}%"
)

latest = st.session_state.latest.copy()
history = st.session_state.history.copy()

total = len(latest)
online = int((latest["Status"] == "ONLINE").sum())
offline = int((latest["Status"] == "OFFLINE").sum())
warnings = int((latest["Status"] == "WARNING").sum())
critical = int((latest["Status"] == "CRITICAL").sum())

a, b, c, d, e = st.columns(5)
a.metric("Total Devices", total)
b.metric("Online", online)
c.metric("Offline", offline)
d.metric("Warnings", warnings)
e.metric("Critical", critical)

st.subheader("Device Health Overview")

col1, col2 = st.columns(2)

with col1:
    selected_type = st.selectbox(
        "Filter by device type",
        ["All", "Router", "Switch", "Server"],
    )

with col2:
    selected_status = st.selectbox(
        "Filter by health status",
        ["All", "ONLINE", "OFFLINE", "WARNING", "CRITICAL"],
    )

filtered = latest.copy()

if selected_type != "All":
    filtered = filtered[filtered["Type"] == selected_type]

if selected_status != "All":
    filtered = filtered[filtered["Status"] == selected_status]

st.caption(f"Showing {len(filtered)} of {total} devices")

def color_status(value):
    colors = {
        "ONLINE": "background-color: #d1fae5; color: #065f46",
        "OFFLINE": "background-color: #fee2e2; color: #991b1b",
        "WARNING": "background-color: #fef3c7; color: #92400e",
        "CRITICAL": "background-color: #fecaca; color: #7f1d1d",
    }
    return colors.get(value, "")

st.dataframe(
    filtered.style.map(color_status, subset=["Status"]),
    width="stretch",
    hide_index=True,
)

# -------------------- PERFORMANCE CHARTS --------------------

st.subheader("Performance Monitoring")

left, right = st.columns(2)

with left:
    st.markdown("**CPU Utilization (%)**")
    st.bar_chart(filtered.set_index("Device")[["CPU Usage (%)"]])

with right:
    st.markdown("**Memory Utilization (%)**")
    st.bar_chart(filtered.set_index("Device")[["Memory Usage (%)"]])

# -------------------- ALERTS --------------------

st.subheader("🚨 Fault Alerts")

alerts = latest[latest["Status"] != "ONLINE"]

if alerts.empty:
    st.success("No faults detected in the latest snapshot.")
else:
    for _, row in alerts.iterrows():
        message = (
            f"{row['Device']} ({row['IP Address']}) — "
            f"{row['Status']}: {row['Alert']}"
        )
        if row["Status"] in ["OFFLINE", "CRITICAL"]:
            st.error(message)
        else:
            st.warning(message)

# -------------------- PERSISTENT HISTORY --------------------

st.subheader("📈 Monitoring History")

if history.empty:
    st.info("Refresh monitoring to collect history.")
else:
    history["Snapshot"] = pd.to_numeric(
        history["Snapshot"], errors="coerce"
    )
    history["CPU Usage (%)"] = pd.to_numeric(
        history["CPU Usage (%)"], errors="coerce"
    )
    history["Memory Usage (%)"] = pd.to_numeric(
        history["Memory Usage (%)"], errors="coerce"
    )

    cpu_history = history.pivot_table(
        index="Snapshot",
        columns="Device",
        values="CPU Usage (%)",
        aggfunc="last",
    ).sort_index()

    memory_history = history.pivot_table(
        index="Snapshot",
        columns="Device",
        values="Memory Usage (%)",
        aggfunc="last",
    ).sort_index()

    st.markdown("**CPU usage across snapshots**")
    st.line_chart(cpu_history)

    st.markdown("**Memory usage across snapshots**")
    st.line_chart(memory_history)

    st.caption(
        f"Saved snapshots: {history['Snapshot'].nunique()} | "
        f"CSV file: {HISTORY_FILE.name}"
    )

    st.download_button(
        "⬇️ Download Complete Monitoring History (CSV)",
        data=history.to_csv(index=False).encode("utf-8"),
        file_name="network_devices.csv",
        mime="text/csv",
    )

st.caption(
    "Educational simulation only. No live SNMP, ping, or device telemetry "
    "is collected."
)