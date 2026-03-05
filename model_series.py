# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 11:29:24 2026

@author: keato
"""

##### 184A IDEAL CSTR SER NPV CALCULATOR #####

#IMPORT RELEVANT LIBRARIES
import numpy as np
from scipy.optimize import fsolve

# ==================

# ANNUALIZATION LAYER

# ==================

def annualize_streams(streams):

    hours_per_year = 8000
    minutes_per_year = hours_per_year * 60

    MW_B = 78.11e-3
    MW_Cl2 = 70.90e-3
    MW_DCB = 147.00e-3
    MW_HCl = 36.46e-3
    MW_CB = 112.56e-3

    # ===== Fresh Feed (for raw material cost) =====
    B_fresh_tpy = streams["F_B_fresh"] * MW_B * minutes_per_year / 1000
    Cl2_fresh_tpy = streams["F_Cl2_fresh"] * MW_Cl2 * minutes_per_year / 1000

    # ===== Effluent (for separation energy) =====
    B_out_tpy = streams["F_B_out"] * MW_B * minutes_per_year / 1000
    Cl2_out_tpy = streams["F_Cl2_out"] * MW_Cl2 * minutes_per_year / 1000
    CB_tpy = streams["F_CB"] * MW_CB * minutes_per_year / 1000
    DCB_tpy = streams["F_DCB"] * MW_DCB * minutes_per_year / 1000
    HCl_tpy = streams["F_HCl"] * MW_HCl * minutes_per_year / 1000
    
    #reacted
    Cl2_reacted_tpy = streams["F_Cl2_reacted"] * MW_Cl2 * minutes_per_year / 1000

    return{
        # fresh
        "B_fresh_tpy": B_fresh_tpy,
        "Cl2_fresh_tpy": Cl2_fresh_tpy,

        # effluent
        "B_out_tpy": B_out_tpy,
        "Cl2_out_tpy": Cl2_out_tpy,
        "CB_tpy": CB_tpy,
        "DCB_tpy": DCB_tpy,
        "HCl_tpy": HCl_tpy,
        "Cl2_reacted_tpy": Cl2_reacted_tpy,

        "V": streams["V"]
    }
    

# =====================

# REVENUE FUNCTION

# =====================

def compute_revenue(annual_streams):
    
    #sell prices ($/tonne)
    price_CB = 1200
    price_DCB = 0
    
    revenue_CB = annual_streams["CB_tpy"] * price_CB
    revenue_DCB = annual_streams["DCB_tpy"] * price_DCB
    
    return revenue_CB + revenue_DCB

# ====================
# VCOP VCOP VCOP VCOP
# ====================

def compute_raw_material_cost(annual_streams):
    
    price_B = 800
    price_Cl2 = 600
    
    cost_B = annual_streams["B_fresh_tpy"] * price_B
    cost_Cl2 = annual_streams["Cl2_fresh_tpy"] * price_Cl2
    
    return cost_B + cost_Cl2


# ====================
# UTILITY ENERGY
# ====================

def compute_reaction_duty(annual_streams):

    deltaH = -105e3
    MW_Cl2 = 70.90e-3

    mol_Cl2_reacted = annual_streams["Cl2_reacted_tpy"] * 1000 / MW_Cl2

    Q_J = abs(deltaH) * mol_Cl2_reacted

    return Q_J / 1e9   # GJ/year


def compute_separator_energy(annual_streams):

    R = 8.314
    T_sep = 300
    lambda_factor = 50

    MW_B = 78.11e-3
    MW_CB = 112.56e-3
    MW_DCB = 147.00e-3
    MW_Cl2 = 70.90e-3

    n_B = annual_streams["B_out_tpy"] * 1000 / MW_B
    n_CB = annual_streams["CB_tpy"] * 1000 / MW_CB
    n_DCB = annual_streams["DCB_tpy"] * 1000 / MW_DCB
    n_Cl2 = annual_streams["Cl2_out_tpy"] * 1000 / MW_Cl2

    n_total = n_B + n_CB + n_DCB + n_Cl2

    z_B = n_B / n_total
    z_CB = n_CB / n_total
    z_DCB = n_DCB / n_total
    z_Cl2 = n_Cl2 / n_total

    Wmin = R * T_sep * (
        n_B * np.log(1/z_B) +
        n_CB * np.log(1/z_CB) +
        n_DCB * np.log(1/z_DCB) +
        n_Cl2 * np.log(1/z_Cl2)
    )

    Wmin_GJ = Wmin / 1e9

    return lambda_factor * Wmin_GJ


# ====================
# UTILITY COSTS
# ====================

def compute_cooling_water_cost(annual_streams, CEPCI=830):

    Q_rxn_GJ = compute_reaction_duty(annual_streams)

    a = 1.3e-4

    cost_per_GJ = a * CEPCI

    return Q_rxn_GJ * cost_per_GJ


def compute_fuel_cost(annual_streams):

    Q_sep_GJ = compute_separator_energy(annual_streams)

    fuel_price = 4.25

    return Q_sep_GJ * fuel_price


def compute_carbon_cost(annual_streams):

    Q_sep_GJ = compute_separator_energy(annual_streams)

    LHV_CH4 = 0.05
    MW_ratio = 44/16

    methane_needed_kg = Q_sep_GJ / LHV_CH4

    CO2_kg = methane_needed_kg * MW_ratio

    CO2_tonnes = CO2_kg / 1000

    carbon_tax = 40

    return CO2_tonnes * carbon_tax


# ====================
# WASTE COSTS
# ====================

def compute_wastewater_treatment_cost(annual_streams, CEPCI=830, fuel_price=4.25):

    wastewater_m3_per_year = annual_streams["HCl_tpy"]

    seconds_per_year = 8000 * 3600
    q = wastewater_m3_per_year / seconds_per_year

    a = 0.001 + 2e-4 * q**(-0.6)
    b = 0.1

    cost_per_m3 = a * CEPCI + b * fuel_price

    return cost_per_m3 * wastewater_m3_per_year


def compute_DCB_disposal_cost(annual_streams):

    cost_per_kg = 2.5e-3

    mass_kg = annual_streams["DCB_tpy"] * 1000

    return mass_kg * cost_per_kg


# ====================
# TOTAL VCOP
# ====================

def compute_VCOP(annual_streams):

    raw_material_cost = compute_raw_material_cost(annual_streams)

    cooling_water_cost = compute_cooling_water_cost(annual_streams)
    fuel_cost = compute_fuel_cost(annual_streams)
    carbon_cost = compute_carbon_cost(annual_streams)

    wastewater_cost = compute_wastewater_treatment_cost(annual_streams)
    DCB_disposal_cost = compute_DCB_disposal_cost(annual_streams)

    VCOP_total = (
        raw_material_cost
        + cooling_water_cost
        + fuel_cost
        + carbon_cost
        + wastewater_cost
        + DCB_disposal_cost
    )

    return {
        "raw_material_cost": raw_material_cost,
        "cooling_water_cost": cooling_water_cost,
        "fuel_cost": fuel_cost,
        "carbon_cost": carbon_cost,
        "wastewater_cost": wastewater_cost,
        "DCB_disposal_cost": DCB_disposal_cost,
        "VCOP": VCOP_total
    }
# ===================

# FCOP FCOP FCOP FCOP

# ===================

def compute_FCOP(annual_streams):

    revenue = compute_revenue(annual_streams)
    
    AGS_fraction = 0.05   # 5% of revenue
    
    AGS = AGS_fraction * revenue
    
    return AGS

# ===================

# CAPEX CAPEX CAPEX

# ===================

def compute_CAPEX_reactor(V_total_m3, N):

    # ---- Cost Index ----
    CEPCI = 830
    CEPCI_ref = 113.7

    # ---- Material & Pressure Factors ----
    Fp = 1.00
    Fm = 2.25
    Fc = Fp * Fm

    # ---- Volume per stage ----
    V_stage_m3 = V_total_m3 / N

    # ---- Convert to ft³ ----
    m3_to_ft3 = 35.3147
    V_stage_ft3 = V_stage_m3 * m3_to_ft3

    # ---- Assume H = D ----
    D_ft = (4 * V_stage_ft3 / np.pi) ** (1/3)
    H_ft = D_ft

    # ---- Cost per reactor ----
    CAPEX_stage = (CEPCI / CEPCI_ref) * 101.9 * \
                  (D_ft ** 1.066) * (H_ft ** 0.82) * (2.18 + Fc)

    # ---- Total reactor CAPEX ----
    CAPEX_total = N * CAPEX_stage

    return CAPEX_total

def compute_CAPEX_separator(annual_streams):

    # ---- Cost per Watt (choose mid-range) ----
    C_per_W = 1.0   # $/W  (within 0.5–1.5 range)

    # ---- Get separation energy ----
    Wreal_GJ_per_year = compute_separator_energy(annual_streams)

    # ---- Convert GJ/year to Watts ----
    seconds_per_year = 365 * 24 * 3600
    Wreal_W = (Wreal_GJ_per_year * 1e9) / seconds_per_year

    # ---- Installed Separator CAPEX ----
    CAPEX_separator = C_per_W * Wreal_W

    return CAPEX_separator

def compute_ISBL(annual_streams, N):

    # Reactor CAPEX
    V_m3 = annual_streams["V"]
    CAPEX_reactor = compute_CAPEX_reactor(V_m3, N)
    
    # Separator CAPEX
    CAPEX_separator = compute_CAPEX_separator(annual_streams)
    
    # Total ISBL
    ISBL_total = CAPEX_reactor + CAPEX_separator
    
    return {
        "CAPEX_reactor": CAPEX_reactor,
        "CAPEX_separator": CAPEX_separator,
        "ISBL": ISBL_total
    }

def compute_OSBL(ISBL):

    OSBL_fraction = 0.40
    
    return OSBL_fraction * ISBL

def compute_contingency(ISBL, OSBL):

    contingency_fraction = 0.25
    
    direct_cost = ISBL + OSBL
    
    return contingency_fraction * direct_cost

def compute_indirect(ISBL, OSBL):

    indirect_fraction = 0.30
    
    direct_cost = ISBL + OSBL
    
    return indirect_fraction * direct_cost

def compute_FCI(ISBL):

    OSBL = compute_OSBL(ISBL)
    
    contingency = compute_contingency(ISBL, OSBL)
    indirect = compute_indirect(ISBL, OSBL)
    
    FCI = ISBL + OSBL + contingency + indirect
    
    return {
        "ISBL": ISBL,
        "OSBL": OSBL,
        "contingency": contingency,
        "indirect": indirect,
        "FCI": FCI
    }

def compute_working_capital(FCI):

    working_capital_fraction = 0.10
    
    return working_capital_fraction * FCI


# ==================

# ECONOMIC ASSUMPTIONS

# ==================

plant_life = 12            # operating years
construction_years = 3     # Year 0–1 construction

tax_rate = 0.22            # corporate tax (US)
discount_rate = 0.15       # required return (WACC)

salvage_fraction = 0.05    # 5% of FCI recovered at shutdown
working_capital_fraction = 0.10   # 10% of FCI (you already used this)

depreciation_years = 10

# =================

# DEPRECIATION FUNCTION

# =================

def compute_straight_line_depreciation(FCI):
    
    annual_dep = FCI / depreciation_years
    
    total_years = construction_years + plant_life
    
    depreciation_schedule = np.zeros(total_years)
    
    for year in range(construction_years, construction_years + depreciation_years):
        
        if year < total_years:
            depreciation_schedule[year] = annual_dep
            
    return depreciation_schedule


# =====================

# CASHFLOW FUNCTION

# =====================

def build_cashflow_model(annual_streams, N):

    # ---- Operating Layer ----
    revenue = compute_revenue(annual_streams)
    VCOP_results = compute_VCOP(annual_streams)
    VCOP = VCOP_results["VCOP"]
    FCOP = compute_FCOP(annual_streams)

    EBITDA = revenue - VCOP - FCOP

    # ---- Capital Layer ----
    ISBL_results = compute_ISBL(annual_streams, N)
    FCI_results = compute_FCI(ISBL_results["ISBL"])
    FCI = FCI_results["FCI"]

    working_capital = compute_working_capital(FCI)
    salvage_value = salvage_fraction * FCI

    # ---- Timeline Length ----
    total_years = construction_years + plant_life
    cashflows = np.zeros(total_years)

    # =========================
    # CONSTRUCTION YEARS
    # =========================

    # Evenly split construction over 3 years
    annual_capex = FCI / construction_years

    for year in range(construction_years):
        cashflows[year] = -annual_capex

    # Working capital at final construction year
    cashflows[construction_years - 1] -= working_capital

    # =========================
    # DEPRECIATION SCHEDULE
    # =========================

    depreciation_schedule = compute_straight_line_depreciation(FCI)

    # =========================
    # OPERATING YEARS
    # =========================

    for year in range(construction_years, total_years):

        depreciation = depreciation_schedule[year]

        taxable_income = EBITDA - depreciation

        taxes = max(tax_rate * taxable_income, 0)

        net_income = taxable_income - taxes

        cashflow = net_income + depreciation

        cashflows[year] = cashflow

    # =========================
    # FINAL YEAR ADJUSTMENTS
    # =========================

    final_year = total_years - 1
    cashflows[final_year] += salvage_value + working_capital

    return {
        "cashflows": cashflows,
        "FCI": FCI,
        "EBITDA": EBITDA,
        "revenue": revenue,
        "VCOP": VCOP,
        "FCOP": FCOP,
        "raw_material_cost": VCOP_results["raw_material_cost"],
        "fuel_cost": VCOP_results["fuel_cost"],
        "carbon_cost": VCOP_results["carbon_cost"],
        "CAPEX_reactor": ISBL_results["CAPEX_reactor"],
        "CAPEX_separator": ISBL_results["CAPEX_separator"],
        "ISBL": ISBL_results["ISBL"]
    }


# =====================
# NPV FUNCTION
# =====================

def compute_NPV(cashflows):

    years = np.arange(len(cashflows))
    
    discounted = cashflows / (1 + discount_rate) ** years
    
    return np.sum(discounted)

# =====================
# IRR FUNCTION
# =====================

def compute_IRR(cashflows, guess=0.1):

    def npv_rate(r):
        years = np.arange(len(cashflows))
        return np.sum(cashflows / (1 + r) ** years)

    r = guess

    for _ in range(100):
        # Derivative of NPV
        years = np.arange(len(cashflows))
        d_npv = np.sum(-years * cashflows / (1 + r) ** (years + 1))

        if abs(d_npv) < 1e-8:
            return np.nan

        r_new = r - npv_rate(r) / d_npv

        if abs(r_new - r) < 1e-8:
            return r_new

        r = r_new

    return np.nan


def optimize_process_series(T_C=30, MR = 3, N = 2):

    T = T_C + 273.15

    Pc_kta = 100.0
    hours_per_year = 8000
    Pc_kg_per_min = Pc_kta * 1e6 / (hours_per_year * 60)
    MW_CB = 112.56e-3
    Pc_mol = Pc_kg_per_min / MW_CB

    k0_1 = 1.03e5
    Ea_1 = 34700
    k0_2 = 4.53e5
    Ea_2 = 42700
    R = 8.314
    rho_molar = 11.3
    C_cat = 0.030

    k1 = k0_1 * np.exp(-Ea_1 / (R * T))
    k2 = k0_2 * np.exp(-Ea_2 / (R * T))

    k1_eff = k1 * C_cat
    k2_eff = k2 * C_cat

    CCl20 = 1.0 / ((1.0 / rho_molar) + (MR / rho_molar))
    CB0 = MR * CCl20

    tau_list = []
    V_list = []
    X_list = []
    S_list = []
    NPV_list = []
    IRR_list = []
    
    B_fresh_list = []
    Cl2_fresh_list = []
    
    CB_list = []
    DCB_list = []
    HCl_list = []
    
    Cl2_recycle_list = []
    F_total_in_list = []
    F_sep_list = []

    tau = 0.1
    delta_tau = 1.05
    target_X = 0.999

    guess = [CB0*0.99, CCl20*0.99, 1e-6, 1e-6, 1e-6]

    X = 0.0
    
    # =======================

    # CSTR DESIGN FUNCTION

    # =======================

    def cstr_stage(vars, tau_stage, C_in):
        
        CB, CCl2, CCB, CDCB, CHCl = vars
        CB_in, CCl2_in, CCB_in, CDCB_in, CHCl_in = C_in
        
        # Reaction rates
        r1 = k1_eff * CB * CCl2
        r2 = k2_eff * CCB * CCl2
        
        # CSTR balances (residual form)
        eq1 = CB_in - CB - tau_stage * r1
        eq2 = CCl2_in - CCl2 - tau_stage * (r1 + r2)
        eq3 = CCB_in - CCB + tau_stage * (r1 - r2)
        eq4 = CDCB_in - CDCB + tau_stage * r2
        eq5 = CHCl_in - CHCl + tau_stage * (r1 + r2)
        
        return [eq1, eq2, eq3, eq4, eq5]

    # ======================
    
    # REACTOR MODEL TAU FUNCTION
    
    # ======================
    
    def reactor_model(tau, guess):
    
        tau_stage = tau / N
    
        # True feed to first stage
        C_in = [CB0, CCl20, 0.0, 0.0, 0.0]
    
        # Use previous solution as solver guess
        current_guess = guess.copy()
    
        for k in range(N):
    
            solution = fsolve(
                cstr_stage,
                current_guess,      # <-- this is the solver guess
                args=(tau_stage, C_in)
            )
    
            # Outlet becomes next stage inlet
            C_in = solution
            current_guess = solution  # update guess for next stage
    
        CB, CCl2, CCB, CDCB, CHCl = C_in
    
        # Conversion
        X = (CCl20 - CCl2) / CCl20
    
        # Selectivity
        if (CCl20 - CCl2) > 1e-12:
            S = CCB / (CCl20 - CCl2)
        else:
            S = 0.0
    
        # Avoid divide-by-zero
        if S * X <= 1e-12:
            return None
    
        # Flow calculations
        F_Cl_in = Pc_mol / (S * X)
        F_B_in = MR * F_Cl_in
    
        F_Cl2_fresh = Pc_mol / S
        F_B_fresh = (Pc_mol / 2.0) * (1 + 1.0 / S)
    
        F_DCB = (Pc_mol / 2.0) * ((1 - S) / S)
    
        F_B_out = F_B_in - Pc_mol - F_DCB
        F_Cl2_out = F_Cl_in - Pc_mol - 2.0 * F_DCB
        F_Cl2_reacted = Pc_mol / S
    
        # Volume
        q = (F_Cl_in + F_B_in) / rho_molar
        V = q * tau * 0.001  # m³ total
    
        return {
            "X": X,
            "S": S,
            "V": V,
            "F_B_in": F_B_in,
            "F_Cl_in": F_Cl_in,
            "F_B_fresh": F_B_fresh,
            "F_Cl2_fresh": F_Cl2_fresh,
            "F_CB": Pc_mol,
            "F_DCB": F_DCB,
            "F_HCl": Pc_mol / S,
            "F_B_out": F_B_out,
            "F_Cl2_out": F_Cl2_out,
            "F_Cl2_reacted": F_Cl2_reacted,
            "solution": C_in
        }





    while X < target_X:

        results = reactor_model(tau, guess)

        X = results["X"]
        S = results["S"]
        V = results["V"]

        guess = results["solution"]

        if S * X < 1e-8:
            tau *= delta_tau
            continue

        annual_streams = annualize_streams(results)

        econ = build_cashflow_model(annual_streams, N)
        cashflows = econ["cashflows"]

        NPV = compute_NPV(cashflows)
        IRR = compute_IRR(cashflows)

        tau_list.append(tau)
        V_list.append(V)
        X_list.append(X)
        S_list.append(S)
        NPV_list.append(NPV)
        IRR_list.append(IRR)
        
        
        # fresh feeds
        B_fresh_list.append(annual_streams["B_fresh_tpy"])
        Cl2_fresh_list.append(annual_streams["Cl2_fresh_tpy"])

        # products
        CB_list.append(annual_streams["CB_tpy"])
        DCB_list.append(annual_streams["DCB_tpy"])
        HCl_list.append(annual_streams["HCl_tpy"])

        # recycle + flow intensities
        Cl2_recycle_list.append(results["F_Cl2_out"] * 60 * hours_per_year / 1e6)
        F_total_in_list.append((results["F_B_in"] + results["F_Cl_in"]) * 60 * hours_per_year / 1e6)
        
        # separation load
        F_sep_list.append(
            annual_streams["B_out_tpy"]
            + annual_streams["Cl2_out_tpy"]
            + annual_streams["CB_tpy"]
            + annual_streams["DCB_tpy"]
        )

        tau *= delta_tau

        if tau > 400000:
            break

    X_array = np.array(X_list)
    S_array = np.array(S_list)
    V_array = np.array(V_list)
    tau_array = np.array(tau_list)
    NPV_array = np.array(NPV_list)
    IRR_array = np.array(IRR_list)
    B_fresh_curve = np.array(B_fresh_list)
    Cl2_fresh_curve = np.array(Cl2_fresh_list)
    
    CB_curve = np.array(CB_list)
    DCB_curve = np.array(DCB_list)
    HCl_curve = np.array(HCl_list)
    
    Cl2_recycle_curve = np.array(Cl2_recycle_list)
    F_total_in_curve = np.array(F_total_in_list)
    
    F_sep_curve = np.array(F_sep_list)

    max_index = np.argmax(NPV_array)

    tau_at_max = tau_array[max_index]
    V_at_max = V_array[max_index]
    X_at_max = X_array[max_index]
    S_at_max = S_array[max_index]
    max_NPV = NPV_array[max_index]
    IRR_at_max = IRR_array[max_index]

    opt_streams = reactor_model(
        tau_at_max,
        [CB0*0.99, CCl20*0.99, 1e-6, 1e-6, 1e-6]
    )

    opt_annual = annualize_streams(opt_streams)
    opt_econ = build_cashflow_model(opt_annual, N)
    
    working_capital = compute_working_capital(opt_econ["FCI"])
    VCOP_results = compute_VCOP(opt_annual)

    ISBL_results = compute_ISBL(opt_annual, N)
    FCI_results = compute_FCI(ISBL_results["ISBL"])

    return {

    "NPV": max_NPV,
    "IRR": IRR_at_max,
    "V": V_at_max,
    "X": X_at_max,
    "S": S_at_max,

    "FCI": opt_econ["FCI"],
    "working_capital": working_capital,
    "VCOP_results": VCOP_results,
    "FCOP": opt_econ["FCOP"],

    "X_curve": X_array,
    "S_curve": S_array,
    "V_curve": V_array,
    "NPV_curve": NPV_array,

    "B_fresh_curve": B_fresh_curve,
    "Cl2_fresh_curve": Cl2_fresh_curve,

    "CB_curve": CB_curve,
    "DCB_curve": DCB_curve,
    "HCl_curve": HCl_curve,

    "Cl2_recycle_curve": Cl2_recycle_curve,
    "F_total_in_curve": F_total_in_curve,
    "F_sep_curve": F_sep_curve
    }



