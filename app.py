import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Family Finance Tracker", layout="wide")

st.title("💰 Family Salary, Expense & Debt Tracker")

# Data files setup
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
DEBTS_FILE = os.path.join(DATA_DIR, "debts.csv")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.csv")

# Defaults
if not os.path.exists(CATEGORIES_FILE):
    pd.DataFrame({"Category": ["Food", "Bills", "Transport", "Shopping", "Other"]}).to_csv(CATEGORIES_FILE, index=False)

if not os.path.exists(ACCOUNTS_FILE):
    pd.DataFrame({"Account Name": ["Cash", "Main Bank Account"], "Balance (LKR)": [0.0, 0.0]}).to_csv(ACCOUNTS_FILE, index=False)

if not os.path.exists(EXPENSES_FILE):
    pd.DataFrame(columns=["Description", "Amount (LKR)", "Category", "Payment Method"]).to_csv(EXPENSES_FILE, index=False)

if not os.path.exists(DEBTS_FILE):
    pd.DataFrame(columns=["Debt Name", "Total Amount", "Paid Amount"]).to_csv(DEBTS_FILE, index=False)

# Load data
accounts_df = pd.read_csv(ACCOUNTS_FILE)
expenses_df = pd.read_csv(EXPENSES_FILE)
debts_df = pd.read_csv(DEBTS_FILE)
categories_df = pd.read_csv(CATEGORIES_FILE)

# Sidebar - Security & Role
st.sidebar.title("🔐 Access Control")
role = st.sidebar.selectbox("Select Role", ["User (Add Expense)", "Admin (Manager)"])

admin_logged_in = False
if role == "Admin (Manager)":
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd == "admin123":  # Oyata kamathi password ekak methanin wenas karaganna puluwan
        admin_logged_in = True
        st.sidebar.success("Admin Access Granted!")
    elif pwd:
        st.sidebar.error("Wrong Password!")

st.sidebar.markdown("---")

# Admin Panel
if admin_logged_in:
    st.sidebar.header("🛠️ Admin Panel")
    
    st.sidebar.subheader("Add Income / Salary")
    inc_desc = st.sidebar.text_input("Income Source", value="Salary")
    inc_amount = st.sidebar.number_input("Income Amount (LKR)", min_value=0.0, step=1000.0)
    inc_account = st.sidebar.selectbox("Deposit to Account", accounts_df["Account Name"].tolist())
    
    if st.sidebar.button("Add Income"):
        if inc_amount > 0:
            accounts_df.loc[accounts_df["Account Name"] == inc_account, "Balance (LKR)"] += inc_amount
            accounts_df.to_csv(ACCOUNTS_FILE, index=False)
            st.sidebar.success(f"Added LKR {inc_amount:,.2f} to {inc_account}!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Add Bank Account / Wallet")
    new_acc = st.sidebar.text_input("New Account Name")
    init_bal = st.sidebar.number_input("Initial Balance", min_value=0.0, step=1000.0)
    if st.sidebar.button("Add Account"):
        if new_acc and new_acc not in accounts_df["Account Name"].values:
            accounts_df = pd.concat([accounts_df, pd.DataFrame({"Account Name": [new_acc], "Balance (LKR)": [init_bal]})], ignore_index=True)
            accounts_df.to_csv(ACCOUNTS_FILE, index=False)
            st.sidebar.success("Account added!")
            st.rerun()

    st.sidebar.subheader("Add Category")
    new_cat = st.sidebar.text_input("New Category Name")
    if st.sidebar.button("Add Category"):
        if new_cat and new_cat not in categories_df["Category"].values:
            categories_df = pd.concat([categories_df, pd.DataFrame({"Category": [new_cat]})], ignore_index=True)
            categories_df.to_csv(CATEGORIES_FILE, index=False)
            st.sidebar.success("Category added!")
            st.rerun()

# User Daily Tracker Panel
st.sidebar.header("📝 Daily Tracker")
st.sidebar.subheader("Add Expense")
exp_desc = st.sidebar.text_input("Expense Description")
exp_amount = st.sidebar.number_input("Expense Amount (LKR)", min_value=0.0, step=100.0)
exp_cat = st.sidebar.selectbox("Category", categories_df["Category"].tolist())
exp_payment_acc = st.sidebar.selectbox("Payment Method (From Account)", accounts_df["Account Name"].tolist())

if st.sidebar.button("Add Expense"):
    if exp_desc and exp_amount > 0:
        # Save expense
        new_row = pd.DataFrame({"Description": [exp_desc], "Amount (LKR)": [exp_amount], "Category": [exp_cat], "Payment Method": [exp_payment_acc]})
        expenses_df = pd.concat([expenses_df, new_row], ignore_index=True)
        expenses_df.to_csv(EXPENSES_FILE, index=False)
        
        # Deduct from account balance
        accounts_df.loc[accounts_df["Account Name"] == exp_payment_acc, "Balance (LKR)"] -= exp_amount
        accounts_df.to_csv(ACCOUNTS_FILE, index=False)
        
        st.sidebar.success("Expense added & balance deducted!")
        st.rerun()
    else:
        st.sidebar.error("Description saha amount ekak danna.")

st.sidebar.markdown("---")
st.sidebar.subheader("Add Debt")
debt_name = st.sidebar.text_input("Debt Name")
debt_total = st.sidebar.number_input("Total Debt", min_value=0.0, step=1000.0)
debt_paid = st.sidebar.number_input("Paid Amount", min_value=0.0, step=1000.0)

if st.sidebar.button("Add Debt"):
    if debt_name:
        debts_df = pd.concat([debts_df, pd.DataFrame({"Debt Name": [debt_name], "Total Amount": [debt_total], "Paid Amount": [debt_paid]})], ignore_index=True)
        debts_df.to_csv(DEBTS_FILE, index=False)
        st.sidebar.success("Debt added!")
        st.rerun()

# Main Screen Dashboard
total_expenses = expenses_df["Amount (LKR)"].sum() if not expenses_df.empty else 0
total_balance = accounts_df["Balance (LKR)"].sum() if not accounts_df.empty else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Bank/Cash Balance", f"LKR {total_balance:,.2f}")
col2.metric("Total Expenses", f"LKR {total_expenses:,.2f}")
rem_debt = (debts_df["Total Amount"] - debts_df["Paid Amount"]).sum() if not debts_df.empty else 0
col3.metric("Remaining Debts", f"LKR {rem_debt:,.2f}")

st.markdown("---")

st.subheader("🏦 Bank Accounts & Cash Wallets Status")
st.dataframe(accounts_df, use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("📋 Expenses List")
    if not expenses_df.empty:
        st.dataframe(expenses_df, use_container_width=True)
    else:
        st.info("No expenses yet.")

with col_b:
    st.subheader("💳 Debts Status")
    if not debts_df.empty:
        d_disp = debts_df.copy()
        d_disp["Remaining"] = d_disp["Total Amount"] - d_disp["Paid Amount"]
        st.dataframe(d_disp, use_container_width=True)
    else:
        st.info("No debts yet.")
