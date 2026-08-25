import streamlit as st
import pandas as pd
import os
import io
from github import Github

st.set_page_config(page_title="Family Finance Tracker", layout="wide")

st.title("💰 Family Finance Tracker)")

# --- GITHUB SYNC SETUP ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    use_github = True
except:
    use_github = False
    st.warning("⚠️ GitHub Secrets not found. Data will only save locally (temporary). Please configure secrets for permanent storage.")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.csv")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
DEBTS_FILE = os.path.join(DATA_DIR, "debts.csv")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.csv")
TRANSFERS_FILE = os.path.join(DATA_DIR, "transfers.csv")

def load_csv_from_github(file_path, default_df):
    if use_github:
        try:
            file_content = repo.get_contents(file_path)
            return pd.read_csv(io.StringIO(file_content.decoded_content.decode("utf-8")))
        except:
            # If file doesn't exist on GitHub yet, create it
            default_df.to_csv(file_path, index=False)
            repo.create_file(file_path, f"Initialize {file_path}", default_df.to_csv(index=False))
            return default_df
    else:
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        else:
            default_df.to_csv(file_path, index=False)
            return default_df

def save_csv_to_github(df, file_path, commit_message):
    csv_string = df.to_csv(index=False)
    # Save locally first
    df.to_csv(file_path, index=False)
    
    if use_github:
        try:
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, commit_message, csv_string, contents.sha)
        except:
            repo.create_file(file_path, commit_message, csv_string)

# Default DataFrames
default_categories = pd.DataFrame({"Category": ["Food", "Bills", "Transport", "Shopping", "Other"]})
default_accounts = pd.DataFrame({"Account Name": ["Indunil's Cash", "Dileema's Cash", "Main Bank Account"], "Balance (LKR)": [0.0, 0.0, 0.0]})
default_expenses = pd.DataFrame(columns=["Date", "Description", "Amount (LKR)", "Category", "Payment Method"])
default_debts = pd.DataFrame(columns=["Debt Name", "Total Amount", "Paid Amount"])
default_transfers = pd.DataFrame(columns=["Date", "From", "To", "Amount (LKR)"])

# Load data from GitHub / Local
categories_df = load_csv_from_github("data/categories.csv", default_categories)
accounts_df = load_csv_from_github("data/accounts.csv", default_accounts)
expenses_df = load_csv_from_github("data/expenses.csv", default_expenses)
debts_df = load_csv_from_github("data/debts.csv", default_debts)
transfers_df = load_csv_from_github("data/transfers.csv", default_transfers)

# Ensure Date column exists
if "Date" not in expenses_df.columns:
    expenses_df["Date"] = pd.Timestamp.today().strftime("%Y-%m-%d")
if "Date" not in transfers_df.columns:
    transfers_df["Date"] = pd.Timestamp.today().strftime("%Y-%m-%d")

# Sidebar - Security & Role
st.sidebar.title("🔐 Access Control")
role = st.sidebar.selectbox("Select Role", ["User (Add Expense/Transfer)", "Admin (Manager)"])

admin_logged_in = False
if role == "Admin (Manager)":
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd == "admin123":
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
    inc_account = st.sidebar.selectbox("Deposit to Account/Wallet", accounts_df["Account Name"].tolist())
    
    if st.sidebar.button("Add Income"):
        if inc_amount > 0:
            accounts_df.loc[accounts_df["Account Name"] == inc_account, "Balance (LKR)"] += inc_amount
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after income")
            st.sidebar.success(f"Added LKR {inc_amount:,.2f} to {inc_account}!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Add Bank Account / Wallet")
    new_acc = st.sidebar.text_input("New Account Name")
    init_bal = st.sidebar.number_input("Initial Balance", min_value=0.0, step=1000.0)
    if st.sidebar.button("Add Account"):
        if new_acc and new_acc not in accounts_df["Account Name"].values:
            accounts_df = pd.concat([accounts_df, pd.DataFrame({"Account Name": [new_acc], "Balance (LKR)": [init_bal]})], ignore_index=True)
            save_csv_to_github(accounts_df, "data/accounts.csv", "Add new account")
            st.sidebar.success("Account added!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Manage / Delete Accounts")
    del_acc = st.sidebar.selectbox("Select Account to Delete", ["--Select--"] + accounts_df["Account Name"].tolist())
    if st.sidebar.button("Delete Account"):
        if del_acc != "--Select--":
            accounts_df = accounts_df[accounts_df["Account Name"] != del_acc]
            save_csv_to_github(accounts_df, "data/accounts.csv", "Delete account")
            st.sidebar.success(f"Deleted {del_acc}!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("✏️ Direct Balance Edit (Admin)")
    edit_acc = st.sidebar.selectbox("Select Account to Edit", accounts_df["Account Name"].tolist(), key="edit_acc")
    current_val = float(accounts_df.loc[accounts_df["Account Name"] == edit_acc, "Balance (LKR)"].values[0])
    new_balance_val = st.sidebar.number_input("New Balance (LKR)", value=current_val, step=100.0)
    
    if st.sidebar.button("Update Balance"):
        accounts_df.loc[accounts_df["Account Name"] == edit_acc, "Balance (LKR)"] = new_balance_val
        save_csv_to_github(accounts_df, "data/accounts.csv", "Direct balance update")
        st.sidebar.success(f"Balance updated successfully for {edit_acc}!")
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Manage Categories")
    new_cat = st.sidebar.text_input("New Category Name")
    if st.sidebar.button("Add Category"):
        if new_cat and new_cat not in categories_df["Category"].values:
            categories_df = pd.concat([categories_df, pd.DataFrame({"Category": [new_cat]})], ignore_index=True)
            save_csv_to_github(categories_df, "data/categories.csv", "Add category")
            st.sidebar.success("Category added!")
            st.rerun()

    del_cat = st.sidebar.selectbox("Select Category to Delete", ["--Select--"] + categories_df["Category"].tolist())
    if st.sidebar.button("Delete Category"):
        if del_cat != "--Select--":
            categories_df = categories_df[categories_df["Category"] != del_cat]
            save_csv_to_github(categories_df, "data/categories.csv", "Delete category")
            st.sidebar.success(f"Deleted category {del_cat}!")
            st.rerun()

# User Daily Tracker Panel
st.sidebar.header("📝 Daily Tracker")
exp_date = st.sidebar.date_input("Expense Date", pd.Timestamp.today())
exp_desc = st.sidebar.text_input("Expense Description")
exp_amount = st.sidebar.number_input("Expense Amount (LKR)", min_value=0.0, step=100.0)
cat_list = categories_df["Category"].tolist() if not categories_df.empty else ["Other"]
exp_cat = st.sidebar.selectbox("Category", cat_list)
exp_payment_acc = st.sidebar.selectbox("Payment Method (From Account/Wallet)", accounts_df["Account Name"].tolist())

if st.sidebar.button("Add Expense"):
    if exp_desc and exp_amount > 0:
        new_row = pd.DataFrame({
            "Date": [str(exp_date)],
            "Description": [exp_desc], 
            "Amount (LKR)": [exp_amount], 
            "Category": [exp_cat], 
            "Payment Method": [exp_payment_acc]
        })
        expenses_df = pd.concat([expenses_df, new_row], ignore_index=True)
        save_csv_to_github(expenses_df, "data/expenses.csv", "Add new expense")
        
        accounts_df.loc[accounts_df["Account Name"] == exp_payment_acc, "Balance (LKR)"] -= exp_amount
        save_csv_to_github(accounts_df, "data/accounts.csv", "Deduct expense from account")
        
        st.sidebar.success("Expense added & balance deducted!")
        st.rerun()
    else:
        st.sidebar.error("Description saha amount ekak danna.")

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Fund Transfer (Bank <-> Cash)")
trans_date = st.sidebar.date_input("Transfer Date", pd.Timestamp.today(), key="t_date")
trans_from = st.sidebar.selectbox("Transfer From", accounts_df["Account Name"].tolist(), key="t_from")
trans_to = st.sidebar.selectbox("Transfer To", accounts_df["Account Name"].tolist(), key="t_to")
trans_amount = st.sidebar.number_input("Transfer Amount (LKR)", min_value=0.0, step=100.0, key="t_amt")

if st.sidebar.button("Transfer Funds"):
    if trans_from == trans_to:
        st.sidebar.error("Source and Destination cannot be the same!")
    elif trans_amount <= 0:
        st.sidebar.error("Please enter a valid amount.")
    else:
        accounts_df.loc[accounts_df["Account Name"] == trans_from, "Balance (LKR)"] -= trans_amount
        accounts_df.loc[accounts_df["Account Name"] == trans_to, "Balance (LKR)"] += trans_amount
        save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after transfer")
        
        t_row = pd.DataFrame({
            "Date": [str(trans_date)],
            "From": [trans_from], 
            "To": [trans_to], 
            "Amount (LKR)": [trans_amount]
        })
        transfers_df = pd.concat([transfers_df, t_row], ignore_index=True)
        save_csv_to_github(transfers_df, "data/transfers.csv", "Add fund transfer")
        
        st.sidebar.success(f"Successfully transferred LKR {trans_amount:,.2f} from {trans_from} to {trans_to}!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Add Debt")
debt_name = st.sidebar.text_input("Debt Name")
debt_total = st.sidebar.number_input("Total Debt", min_value=0.0, step=1000.0)
debt_paid = st.sidebar.number_input("Paid Amount", min_value=0.0, step=1000.0)

if st.sidebar.button("Add Debt"):
    if debt_name:
        debts_df = pd.concat([debts_df, pd.DataFrame({"Debt Name": [debt_name], "Total Amount": [debt_total], "Paid Amount": [debt_paid]})], ignore_index=True)
        save_csv_to_github(debts_df, "data/debts.csv", "Add debt")
        st.sidebar.success("Debt added!")
        st.rerun()

# --- MAIN DASHBOARD ---
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

# --- REPORTS ---
st.markdown("---")
st.subheader("📊 Expense & Financial Reports")

if not expenses_df.empty:
    expenses_df["Date"] = pd.to_datetime(expenses_df["Date"])
    report_type = st.selectbox("Select Report View", ["All Time", "Daily", "Weekly", "Monthly"])
    
    filtered_expenses = expenses_df.copy()
    if report_type == "Daily":
        selected_date = st.date_input("Select Date", pd.Timestamp.today())
        filtered_expenses = expenses_df[expenses_df["Date"].dt.date == selected_date]
    elif report_type == "Weekly":
        year = st.number_input("Year", min_value=2024, max_value=2030, value=pd.Timestamp.today().year)
        week_num = st.number_input("Week Number", min_value=1, max_value=52, value=int(pd.Timestamp.today().strftime("%U")))
        filtered_expenses = expenses_df[(expenses_df["Date"].dt.year == year) & (expenses_df["Date"].dt.isocalendar().week == week_num)]
    elif report_type == "Monthly":
        month_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        sel_month_name = st.selectbox("Select Month", month_list, index=pd.Timestamp.today().month - 1)
        sel_month_num = month_list.index(sel_month_name) + 1
        sel_year = st.number_input("Year", min_value=2024, max_value=2030, value=pd.Timestamp.today().year, key="m_year")
        filtered_expenses = expenses_df[(expenses_df["Date"].dt.month == sel_month_num) & (expenses_df["Date"].dt.year == sel_year)]

    st.write(f"Showing expenses for: **{report_type}**")
    if not filtered_expenses.empty:
        disp_exp = filtered_expenses.copy()
        disp_exp["Date"] = disp_exp["Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(disp_exp, use_container_width=True)
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.metric(f"Total Expenses ({report_type})", f"LKR {disp_exp['Amount (LKR)'].sum():,.2f}")
        with col_r2:
            st.download_button(f"📥 Download {report_type} Expenses CSV", disp_exp.to_csv(index=False), f"expenses_{report_type.lower()}.csv", "text/csv")
        
        st.subheader(f"📈 Breakdown by Category ({report_type})")
        cat_breakdown = disp_exp.groupby("Category")["Amount (LKR)"].sum()
        st.bar_chart(cat_breakdown)
    else:
        st.info(f"No expenses found for this {report_type.lower()} filter.")
else:
    st.info("No expense data available for reports yet.")

st.markdown("---")
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("📋 Full Expenses List")
    if not expenses_df.empty:
        d_exp_full = expenses_df.copy()
        d_exp_full["Date"] = pd.to_datetime(d_exp_full["Date"]).dt.strftime("%Y-%m-%d")
        st.dataframe(d_exp_full, use_container_width=True)
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

if not transfers_df.empty:
    st.markdown("---")
    st.subheader("🔄 Recent Fund Transfers")
    st.dataframe(transfers_df, use_container_width=True)

