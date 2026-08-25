import streamlit as st
import pandas as pd
import os
import io
from github import Github

st.set_page_config(page_title="Family Finance Tracker", layout="wide")

st.title("💰 Family Finnace Tracker")

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
INCOMES_FILE = os.path.join(DATA_DIR, "incomes.csv")

def load_csv_from_github(file_path, default_df):
    if use_github:
        try:
            file_content = repo.get_contents(file_path)
            return pd.read_csv(io.StringIO(file_content.decoded_content.decode("utf-8")))
        except:
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
default_incomes = pd.DataFrame(columns=["Date", "Income Source", "Amount (LKR)", "Account"])
default_debts = pd.DataFrame(columns=["Type", "Person/Entity", "Total Amount", "Paid Amount", "Note"])
default_transfers = pd.DataFrame(columns=["Date", "From", "To", "Amount (LKR)"])

# Load data from GitHub / Local
categories_df = load_csv_from_github("data/categories.csv", default_categories)
accounts_df = load_csv_from_github("data/accounts.csv", default_accounts)
expenses_df = load_csv_from_github("data/expenses.csv", default_expenses)
incomes_df = load_csv_from_github("data/incomes.csv", default_incomes)
debts_df = load_csv_from_github("data/debts.csv", default_debts)
transfers_df = load_csv_from_github("data/transfers.csv", default_transfers)

# Ensure Date columns exist
for df_obj, col_name in [(expenses_df, "Date"), (transfers_df, "Date"), (incomes_df, "Date")]:
    if col_name not in df_obj.columns:
        df_obj[col_name] = pd.Timestamp.today().strftime("%Y-%m-%d")

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
    inc_date = st.sidebar.date_input("Income Date", pd.Timestamp.today(), key="inc_d")
    inc_desc = st.sidebar.text_input("Income Source", value="Salary")
    inc_amount = st.sidebar.number_input("Income Amount (LKR)", min_value=0.0, step=1000.0)
    inc_account = st.sidebar.selectbox("Deposit to Account/Wallet", accounts_df["Account Name"].tolist())
    
    if st.sidebar.button("Add Income"):
        if inc_amount > 0:
            accounts_df.loc[accounts_df["Account Name"] == inc_account, "Balance (LKR)"] += inc_amount
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after income")
            
            new_inc = pd.DataFrame({
                "Date": [str(inc_date)],
                "Income Source": [inc_desc],
                "Amount (LKR)": [inc_amount],
                "Account": [inc_account]
            })
            incomes_df = pd.concat([incomes_df, new_inc], ignore_index=True)
            save_csv_to_github(incomes_df, "data/incomes.csv", "Add income record")
            
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
st.sidebar.subheader("🤝 Debts & Lending Management")
debt_type = st.sidebar.selectbox("Transaction Type", ["Borrowing (Nayata Gatta)", "Lending (Nayata Dunna)"])
person_name = st.sidebar.text_input("Person / Institution Name")
debt_total = st.sidebar.number_input("Total Amount", min_value=0.0, step=1000.0)
debt_paid = st.sidebar.number_input("Paid / Settled Amount", min_value=0.0, step=1000.0)
debt_note = st.sidebar.text_input("Note / Description")

if st.sidebar.button("Add Debt / Lending"):
    if person_name and debt_total > 0:
        new_debt = pd.DataFrame({
            "Type": [debt_type],
            "Person/Entity": [person_name],
            "Total Amount": [debt_total],
            "Paid Amount": [debt_paid],
            "Note": [debt_note]
        })
        debts_df = pd.concat([debts_df, new_debt], ignore_index=True)
        save_csv_to_github(debts_df, "data/debts.csv", "Add debt or lending")
        st.sidebar.success("Successfully recorded!")
        st.rerun()
    else:
        st.sidebar.error("Please fill name and total amount.")

# --- MAIN DASHBOARD ---
total_expenses = expenses_df["Amount (LKR)"].sum() if not expenses_df.empty else 0
total_balance = accounts_df["Balance (LKR)"].sum() if not accounts_df.empty else 0
total_incomes = incomes_df["Amount (LKR)"].sum() if not incomes_df.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Balance", f"LKR {total_balance:,.2f}")
col2.metric("Total Incomes", f"LKR {total_incomes:,.2f}")
col3.metric("Total Expenses", f"LKR {total_expenses:,.2f}")

if not debts_df.empty:
    borrow_df = debts_df[debts_df["Type"] == "Borrowing (Nayata Gatta)"]
    lend_df = debts_df[debts_df["Type"] == "Lending (Nayata Dunna)"]
    rem_borrow = (borrow_df["Total Amount"] - borrow_df["Paid Amount"]).sum() if not borrow_df.empty else 0
    rem_lend = (lend_df["Total Amount"] - lend_df["Paid Amount"]).sum() if not lend_df.empty else 0
    col4.metric("Net Debt Position", f"LKR {rem_borrow - rem_lend:,.2f}")
else:
    col4.metric("Net Debt Position", "LKR 0.00")

st.markdown("---")
st.subheader("🏦 Bank Accounts & Cash Wallets Status")
st.dataframe(accounts_df, use_container_width=True)

# --- REPORTS WITH CUSTOM DATE RANGE ---
st.markdown("---")
st.subheader("📊 Advanced Financial Reports (Custom Date Range & Filters)")

if not expenses_df.empty or not incomes_df.empty:
    # Convert dates
    if not expenses_df.empty:
        expenses_df["Date"] = pd.to_datetime(expenses_df["Date"])
    if not incomes_df.empty:
        incomes_df["Date"] = pd.to_datetime(incomes_df["Date"])

    report_mode = st.selectbox("Select Report Category", ["Expenses Report", "Incomes Report"])
    
    st.write("### 📅 Select Custom Date Range")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Start Date", pd.Timestamp.today() - pd.Timedelta(days=30))
    with col_d2:
        end_date = st.date_input("End Date", pd.Timestamp.today())

    if report_mode == "Expenses Report":
        if not expenses_df.empty:
            filtered_exp = expenses_df[(expenses_df["Date"].dt.date >= start_date) & (expenses_df["Date"].dt.date <= end_date)]
            st.write(f"Showing Expenses from **{start_date}** to **{end_date}**")
            
            if not filtered_exp.empty:
                disp_exp = filtered_exp.copy()
                disp_exp["Date"] = disp_exp["Date"].dt.strftime("%Y-%m-%d")
                st.dataframe(disp_exp, use_container_width=True)
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.metric("Total Expenses (Selected Range)", f"LKR {disp_exp['Amount (LKR)'].sum():,.2f}")
                with col_r2:
                    st.download_button("📥 Download Filtered Expenses CSV", disp_exp.to_csv(index=False), "filtered_expenses.csv", "text/csv")
                
                st.subheader("📈 Breakdown by Category")
                cat_breakdown = disp_exp.groupby("Category")["Amount (LKR)"].sum()
                st.bar_chart(cat_breakdown)
            else:
                st.info("No expenses found for this date range.")
        else:
            st.info("No expense data available.")

    elif report_mode == "Incomes Report":
        if not incomes_df.empty:
            filtered_inc = incomes_df[(incomes_df["Date"].dt.date >= start_date) & (incomes_df["Date"].dt.date <= end_date)]
            st.write(f"Showing Incomes from **{start_date}** to **{end_date}**")
            
            if not filtered_inc.empty:
                disp_inc = filtered_inc.copy()
                disp_inc["Date"] = disp_inc["Date"].dt.strftime("%Y-%m-%d")
                st.dataframe(disp_inc, use_container_width=True)
                
                col_i1, col_i2 = st.columns(2)
                with col_i1:
                    st.metric("Total Incomes (Selected Range)", f"LKR {disp_inc['Amount (LKR)'].sum():,.2f}")
                with col_i2:
                    st.download_button("📥 Download Filtered Incomes CSV", disp_inc.to_csv(index=False), "filtered_incomes.csv", "text/csv")
            else:
                st.info("No incomes found for this date range.")
        else:
            st.info("No income data available.")
else:
    st.info("No financial data available yet.")

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
    st.subheader("🤝 Debts & Lending Tracking")
    if not debts_df.empty:
        d_disp = debts_df.copy()
        d_disp["Remaining Balance"] = d_disp["Total Amount"] - d_disp["Paid Amount"]
        st.dataframe(d_disp, use_container_width=True)
    else:
        st.info("No debts or lendings recorded yet.")

if not transfers_df.empty:
    st.markdown("---")
    st.subheader("🔄 Recent Fund Transfers")
    st.dataframe(transfers_df, use_container_width=True)
