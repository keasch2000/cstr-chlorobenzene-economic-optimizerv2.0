# -*- coding: utf-8 -*-

import streamlit as st
import matplotlib.pyplot as plt
import model_series
import io
import numpy as np


def run_case(args):
    T, MR, N = args
    res = model_series.optimize_process_series(T_C=T, MR=MR, N=N)
    return res["NPV"]


def parallel_sweep(param_values, T_C, MR, N, mode):

    results = []

    for val in param_values:

        if mode == "T":
            res = model_series.optimize_process_series(T_C=val, MR=MR, N=N)

        elif mode == "MR":
            res = model_series.optimize_process_series(T_C=T_C, MR=val, N=N)

        elif mode == "N":
            res = model_series.optimize_process_series(T_C=T_C, MR=MR, N=int(val))

        results.append(res["NPV"])

    return results

# -----------------------------
# Figure Export Function
# -----------------------------

def export_figure(fig, filename_base):

    buf_png = io.BytesIO()
    fig.savefig(buf_png, format="png", dpi=300, bbox_inches="tight")
    buf_png.seek(0)

    st.download_button(
        "Download PNG",
        data=buf_png,
        file_name=f"{filename_base}.png",
        mime="image/png",
        use_container_width=True
    )

    buf_pdf = io.BytesIO()
    fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
    buf_pdf.seek(0)

    st.download_button(
        "Download PDF",
        data=buf_pdf,
        file_name=f"{filename_base}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# -----------------------------
# Plot Styling
# -----------------------------

plt.style.use("default")

plt.rcParams.update({
    "figure.dpi":300,
    "savefig.dpi":300,
    "font.size":14,
    "axes.labelsize":16,
    "axes.titlesize":18,
    "xtick.labelsize":13,
    "ytick.labelsize":13,
    "legend.fontsize":12,
    "lines.linewidth":2.5,
    "axes.linewidth":1.2,
})

# -----------------------------
# Page Layout
# -----------------------------

st.set_page_config(layout="wide")

st.title("ChE 184A Series CSTR Economic Optimizer")
st.markdown("Adjust operating conditions in sidebar.")



# -----------------------------
# Sidebar Controls
# -----------------------------

st.sidebar.header("Operating Conditions")

T_C = st.sidebar.slider("Reactor Temperature (°C)",25,50,40)
MR = st.sidebar.slider("Molar Ratio (B/Cl₂)",1.0,20.0,10.0,0.5)
N  = st.sidebar.slider("Number of CSTR in Series",1,10,3)

run_button = st.sidebar.button("Run Optimization")

st.sidebar.markdown("---")
st.sidebar.header("Sensitivity Analysis")

run_T_sweep = st.sidebar.button("Temperature Sweep")
run_MR_sweep = st.sidebar.button("MR Sweep")
run_N_sweep = st.sidebar.button("Reactor Count Sweep")

# -----------------------------
# Session State Storage
# -----------------------------

if "results" not in st.session_state:
    st.session_state.results = None
    
if "T_sweep" not in st.session_state:
    st.session_state.T_sweep = None

if "MR_sweep" not in st.session_state:
    st.session_state.MR_sweep = None

if "N_sweep" not in st.session_state:
    st.session_state.N_sweep = None

# -----------------------------
# Run Model Only When Button Pressed
# -----------------------------

if run_button:

    with st.spinner("Running reactor + economic optimization..."):
        st.session_state.results = model_series.optimize_process_series(
            T_C=T_C,
            MR=MR,
            N=N
        )

results = st.session_state.results

# -----------------------------
# Stop if no results yet
# -----------------------------

if results is None:
    st.info("Adjust parameters and press **Run Optimization**.")
    st.stop()

# -----------------------------
# Metrics
# -----------------------------

col1,col2,col3 = st.columns(3)

col1.metric("NPV ($)",f"{results['NPV']:,.0f}")
col2.metric("IRR (%)",f"{results['IRR']*100:,.2f}")
col3.metric("Reactor Volume (m³)",f"{results['V']:,.2f}")

col4,col5 = st.columns(2)

col4.metric("Conversion (X)",f"{results['X']:.4f}")
col5.metric("Selectivity (S)",f"{results['S']:.4f}")

st.markdown("---")

# -----------------------------
# Cost Summary
# -----------------------------

st.subheader("Capital & Operating Summary")

st.write(f"**FCI:** ${results['FCI']:,.0f}")
st.write(f"**Working Capital:** ${results['working_capital']:,.0f}")
st.write(f"**VCOP:** ${results['VCOP_results']['VCOP']:,.0f}")
st.write(f"**FCOP:** ${results['FCOP']:,.0f}")

st.markdown("---")

# -----------------------------
# Mass Balance at Optimum
# -----------------------------

st.subheader("Mass Balance (Optimal Operating Point)")

# index of optimal NPV
opt_idx = np.argmax(results["NPV_curve"])

# Inlet flows
B_in = results["B_fresh_curve"][opt_idx]
Cl2_in = results["Cl2_fresh_curve"][opt_idx]
Cl2_recycle = results["Cl2_recycle_curve"][opt_idx]

# Outlet flows
CB_out = results["CB_curve"][opt_idx]
DCB_out = results["DCB_curve"][opt_idx]
HCl_out = results["HCl_curve"][opt_idx]

total_in = B_in + Cl2_in + Cl2_recycle
total_out = CB_out + DCB_out + HCl_out + Cl2_recycle

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Inlet Streams (kmol/min)**")
    st.write(f"Benzene Fresh: {B_in:,.2f}")
    st.write(f"Chlorine Fresh: {Cl2_in:,.2f}")
    st.write(f"Chlorine Recycle: {Cl2_recycle:,.2f}")
    st.write(f"**Total In:** {total_in:,.2f}")

with col2:
    st.markdown("**Outlet Streams (kmol/min)**")
    st.write(f"Chlorobenzene: {CB_out:,.2f}")
    st.write(f"Dichlorobenzene: {DCB_out:,.2f}")
    st.write(f"HCl: {HCl_out:,.2f}")
    st.write(f"Cl₂ Recycle: {Cl2_recycle:,.2f}")
    st.write(f"**Total Out:** {total_out:,.2f}")

closure_error = (total_out - total_in)/total_in * 100


closure_error = abs((total_out - total_in) / total_in) * 100

st.markdown("---")
st.subheader("Mass Balance Check")

col1, col2 = st.columns(2)

with col1:
    st.metric("Relative Error (%)", f"{closure_error:.5f}")

with col2:

    if closure_error < 0.1:
        st.success("Mass Balance Closed ✓")

    elif closure_error < 1:
        st.warning("Mass Balance Nearly Closed")

    else:
        st.error("Mass Balance Not Closed")
        


st.markdown("---")
st.header("Process Performance Plots")

# -----------------------------
# Data Prep
# -----------------------------

X_curve = results["X_curve"]
S_curve = results["S_curve"]
NPV_curve = results["NPV_curve"]
V_curve = results["V_curve"]

B_fresh = results["B_fresh_curve"]/1000
Cl2_fresh = results["Cl2_fresh_curve"]/1000
CB = results["CB_curve"]/1000
DCB = results["DCB_curve"]/1000
HCl = results["HCl_curve"]/1000
Cl2_recycle = results["Cl2_recycle_curve"]/1000
F_total = results["F_total_in_curve"]/1000
F_sep = results["F_sep_curve"]/1000

# -----------------------------
# Row 1
# -----------------------------

col1,col2 = st.columns(2)

with col1:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,NPV_curve)
    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("NPV (MM$)")
    ax.set_xlim(0,1)
    ax.set_ylim(-30e6,30e6)
    ax.set_title("NPV vs Conversion")
    ax.yaxis.set_major_formatter(lambda x,_:f"{x/1e6:.0f}")

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"NPV_vs_conversion")

with col2:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(S_curve,NPV_curve)
    ax.set_xlabel("Selectivity (S)")
    ax.set_ylabel("NPV (MM$)")
    ax.set_xlim(0.75,1.0)
    ax.set_ylim(-30e6,30e6)
    ax.set_title("NPV vs Selectivity")
    ax.yaxis.set_major_formatter(lambda x,_:f"{x/1e6:.0f}")

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"NPV_vs_selectivity")

# -----------------------------
# Row 2
# -----------------------------

col3,col4 = st.columns(2)

with col3:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,S_curve)
    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("Selectivity (S)")
    ax.set_xlim(0,1)
    ax.set_ylim(0.8,1.0)
    ax.set_title("Selectivity vs Conversion")

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"Selectivity_vs_conversion")

with col4:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,V_curve)
    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("Reactor Volume (m³)")
    ax.set_xlim(0,1)
    ax.set_ylim(0,200)
    ax.set_title("Reactor Volume vs Conversion")

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"Reactor_volume_vs_conversion")

# -----------------------------
# Row 3
# -----------------------------

col5,col6 = st.columns(2)

with col5:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,B_fresh,label="Benzene Fresh")
    ax.plot(X_curve,Cl2_fresh,label="Chlorine Fresh")

    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("Fresh Feed (kta)")
    ax.set_xlim(0,1)
    ax.set_title("Fresh Feed vs Conversion")
    ax.legend()

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"Fresh_feed_vs_conversion")

with col6:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,CB,label="CB")
    ax.plot(X_curve,DCB,label="DCB")
    ax.plot(X_curve,HCl,label="HCl")

    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("Production (kta)")
    ax.set_xlim(0,1)
    ax.set_title("Product Production vs Conversion")
    ax.legend()

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"Production_vs_conversion")

# -----------------------------
# Row 4
# -----------------------------

col7,col8 = st.columns(2)

with col7:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,Cl2_recycle)

    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("Chlorine Recycle (kta)")
    ax.set_xlim(0,0.5)

    ymax=max(Cl2_recycle)
    ax.set_ylim(-0.05*ymax,1.05*ymax)

    ax.set_title("Chlorine Recycle vs Conversion")

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"Chlorine_recycle_vs_conversion")

with col8:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,F_total)

    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("Total Reactor Feed (kta)")
    ax.set_xlim(0,0.5)

    ax.set_title("Total Reactor Feed vs Conversion")

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"Total_feed_vs_conversion")

# -----------------------------
# Row 5
# -----------------------------

col9,_ = st.columns(2)

with col9:

    fig,ax = plt.subplots(figsize=(6,4.5))

    ax.plot(X_curve,F_sep)

    ax.set_xlabel("Conversion (X)")
    ax.set_ylabel("Separation Load (kta)")
    ax.set_xlim(0,0.5)

    ax.set_title("Separation Load vs Conversion")

    fig.tight_layout()

    st.pyplot(fig)
    export_figure(fig,"Separation_load_vs_conversion")
    
    
    


st.markdown("---")
st.subheader("Sensitivity Analysis at Optimal Conditions")


    
if run_T_sweep:
    temps = np.linspace(25,50,20)

    with st.spinner("Running temperature sensitivity..."):
        st.session_state.T_sweep = parallel_sweep(temps, T_C, MR, N, "T")

if st.session_state.T_sweep is not None:

    temps = np.linspace(25,80,20)

    fig, ax = plt.subplots()

    npv_vals = st.session_state.T_sweep

    ax.plot(temps, np.array(npv_vals)/1e6)
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("NPV (MM$)")
    ax.set_title(f"Optimal NPV vs Temperature (MR = {MR:.2f}, N = {N})")

    st.pyplot(fig)
    export_figure(fig,"NPV_vs_temperature")
    
if run_MR_sweep:
    mrs = np.linspace(1,20,25)

    with st.spinner("Running MR sensitivity..."):
        st.session_state.MR_sweep = parallel_sweep(mrs, T_C, MR, N, "MR")

if st.session_state.MR_sweep is not None:

    mrs = np.linspace(1,20,25)

    fig, ax = plt.subplots()

    npv_vals = st.session_state.MR_sweep

    ax.plot(mrs, np.array(npv_vals)/1e6)
    ax.set_xlabel("Molar Ratio (B/Cl₂)")
    ax.set_ylabel("NPV (MM$)")
    ax.set_title(f"Optimal NPV vs Molar Ratio (T = {T_C} °C, N = {N})")

    st.pyplot(fig)
    export_figure(fig,"NPV_vs_MR")
    
if run_N_sweep:
    Ns = np.arange(1,10)

    with st.spinner("Running reactor count sensitivity..."):
        st.session_state.N_sweep = parallel_sweep(Ns, T_C, MR, N, "N")

if st.session_state.N_sweep is not None:

    Ns = np.arange(1,10)

    fig, ax = plt.subplots()

    npv_vals = st.session_state.N_sweep

    ax.plot(Ns, np.array(npv_vals)/1e6)
    ax.set_xlabel("Number of CSTRs")
    ax.set_ylabel("NPV (MM$)")
    ax.set_title(f"Optimal NPV vs Reactor Count (T = {T_C} °C, MR = {MR:.2f})")

    st.pyplot(fig)
    export_figure(fig,"NPV_vs_reactor_count")