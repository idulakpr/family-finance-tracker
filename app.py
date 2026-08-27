import streamlit as st
import pandas as pd
import os
import io
from github import Github

st.set_page_config(page_title="Family Finance Tracker", layout="wide")

st.title("💰 Family Finance Tracke")

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
default_debts = pd.DataFrame(columns=["Type", "Person/Entity", "Total Amount", "Paid Amount", "Account", "Note"])
default_transfers = pd.DataFrame(columns=["Date", "From", "To", "Amount (LKR)"])

# Load data from GitHub / Local
categories_df = load_csv_from_github("data/categories.csv", default_categories)
accounts_df = load_csv_from_github("data/accounts.csv", default_accounts)
expenses_df = load_csv_from_github("data/expenses.csv", default_expenses)
incomes_df = load_csv_from_github("data/incomes.csv", default_incomes)
debts_df = load_csv_from_github("data/debts.csv", default_debts)
transfers_df = load_csv_from_github("data/transfers.csv", default_transfers)

# Ensure necessary columns exist for backward compatibility
if "Account" not in debts_df.columns:
    debts_df["Account"] = accounts_df["Account Name"].iloc[0] if not accounts_df.empty else "Cash"

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
    st.sidebar.subheader("✏️ Edit / Delete Incomes")
    if not incomes_df.empty:
        inc_indices = list(range(len(incomes_df)))
        sel_inc_idx = st.sidebar.selectbox("Select Income Record to Modify", inc_indices, format_func=lambda x: f"{incomes_df.loc[x, 'Date']} | {incomes_df.loc[x, 'Income Source']} | LKR {incomes_df.loc[x, 'Amount (LKR)']:,.2f}")
        
        edit_inc_amount = st.sidebar.number_input("New Amount", value=float(incomes_df.loc[sel_inc_idx, "Amount (LKR)"]), step=100.0, key="e_inc_amt")
        edit_inc_acc = st.sidebar.selectbox("New Account", accounts_df["Account Name"].tolist(), index=accounts_df["Account Name"].tolist().index(incomes_df.loc[sel_inc_idx, "Account"]) if incomes_df.loc[sel_inc_idx, "Account"] in accounts_df["Account Name"].tolist() else 0, key="e_inc_acc")
        
        col_ie1, col_ie2 = st.sidebar.columns(2)
        if col_ie1.button("Update Income"):
            old_amt = float(incomes_df.loc[sel_inc_idx, "Amount (LKR)"])
            old_acc = incomes_df.loc[sel_inc_idx, "Account"]
            
            if old_acc in accounts_df["Account Name"].values:
                accounts_df.loc[accounts_df["Account Name"] == old_acc, "Balance (LKR)"] -= old_amt
            accounts_df.loc[accounts_df["Account Name"] == edit_inc_acc, "Balance (LKR)"] += edit_inc_amount
            
            incomes_df.loc[sel_inc_idx, "Amount (LKR)"] = edit_inc_amount
            incomes_df.loc[sel_inc_idx, "Account"] = edit_inc_acc
            
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after income edit")
            save_csv_to_github(incomes_df, "data/incomes.csv", "Update income record")
            st.sidebar.success("Income updated successfully!")
            st.rerun()
            
        if col_ie2.button("Delete Income"):
            old_amt = float(incomes_df.loc[sel_inc_idx, "Amount (LKR)"])
            old_acc = incomes_df.loc[sel_inc_idx, "Account"]
            if old_acc in accounts_df["Account Name"].values:
                accounts_df.loc[accounts_df["Account Name"] == old_acc, "Balance (LKR)"] -= old_amt
            
            incomes_df = incomes_df.drop(sel_inc_idx).reset_index(drop=True)
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after income deletion")
            save_csv_to_github(incomes_df, "data/incomes.csv", "Delete income record")
            st.sidebar.success("Income deleted!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("✏️ Edit / Delete Expenses")
    if not expenses_df.empty:
        exp_indices = list(range(len(expenses_df)))
        sel_exp_idx = st.sidebar.selectbox("Select Expense Record to Modify", exp_indices, format_func=lambda x: f"{expenses_df.loc[x, 'Date']} | {expenses_df.loc[x, 'Description']} | LKR {expenses_df.loc[x, 'Amount (LKR)']:,.2f}")
        
        edit_exp_amt = st.sidebar.number_input("New Expense Amount", value=float(expenses_df.loc[sel_exp_idx, "Amount (LKR)"]), step=100.0, key="e_exp_amt")
        edit_exp_acc = st.sidebar.selectbox("New Payment Method", accounts_df["Account Name"].tolist(), index=accounts_df["Account Name"].tolist().index(expenses_df.loc[sel_exp_idx, "Payment Method"]) if expenses_df.loc[sel_exp_idx, "Payment Method"] in accounts_df["Account Name"].tolist() else 0, key="e_exp_acc")
        
        col_ee1, col_ee2 = st.sidebar.columns(2)
        if col_ee1.button("Update Expense"):
            old_amt = float(expenses_df.loc[sel_exp_idx, "Amount (LKR)"])
            old_acc = expenses_df.loc[sel_exp_idx, "Payment Method"]
            
            if old_acc in accounts_df["Account Name"].values:
                accounts_df.loc[accounts_df["Account Name"] == old_acc, "Balance (LKR)"] += old_amt
            accounts_df.loc[accounts_df["Account Name"] == edit_exp_acc, "Balance (LKR)"] -= edit_exp_amt
            
            expenses_df.loc[sel_exp_idx, "Amount (LKR)"] = edit_exp_amt
            expenses_df.loc[sel_exp_idx, "Payment Method"] = edit_exp_acc
            
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after expense edit")
            save_csv_to_github(expenses_df, "data/expenses.csv", "Update expense record")
            st.sidebar.success("Expense updated successfully!")
            st.rerun()
            
        if col_ee2.button("Delete Expense"):
            old_amt = float(expenses_df.loc[sel_exp_idx, "Amount (LKR)"])
            old_acc = expenses_df.loc[sel_exp_idx, "Payment Method"]
            if old_acc in accounts_df["Account Name"].values:
                accounts_df.loc[accounts_df["Account Name"] == old_acc, "Balance (LKR)"] += old_amt
            
            expenses_df = expenses_df.drop(sel_exp_idx).reset_index(drop=True)
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after expense deletion")
            save_csv_to_github(expenses_df, "data/expenses.csv", "Delete expense record")
            st.sidebar.success("Expense deleted!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 Delete Fund Transfers")
    if not transfers_df.empty:
        trans_indices = list(range(len(transfers_df)))
        sel_trans_idx = st.sidebar.selectbox("Select Transfer to Delete", trans_indices, format_func=lambda x: f"{transfers_df.loc[x, 'Date']} | {transfers_df.loc[x, 'From']} ➡️ {transfers_df.loc[x, 'To']} | LKR {transfers_df.loc[x, 'Amount (LKR)']:,.2f}")
        
        if st.sidebar.button("Delete Transfer"):
            tr_amt = float(transfers_df.loc[sel_trans_idx, "Amount (LKR)"])
            tr_from = transfers_df.loc[sel_trans_idx, "From"]
            tr_to = transfers_df.loc[sel_trans_idx, "To"]
            
            # Reverse transfer effect on accounts
            if tr_from in accounts_df["Account Name"].values:
                accounts_df.loc[accounts_df["Account Name"] == tr_from, "Balance (LKR)"] += tr_amt
            if tr_to in accounts_df["Account Name"].values:
                accounts_df.loc[accounts_df["Account Name"] == tr_to, "Balance (LKR)"] -= tr_amt
                
            transfers_df = transfers_df.drop(sel_trans_idx).reset_index(drop=True)
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after transfer deletion")
            save_csv_to_github(transfers_df, "data/transfers.csv", "Delete transfer record")
            st.sidebar.success("Transfer deleted and balances reverted!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🤝 Settle / Delete Debts & Lending")
    if not debts_df.empty:
        debt_indices = list(range(len(debts_df)))
        sel_debt_idx = st.sidebar.selectbox("Select Debt/Lending Record", debt_indices, format_func=lambda x: f"{debts_df.loc[x, 'Type']} | {debts_df.loc[x, 'Person/Entity']} | Total: {debts_df.loc[x, 'Total Amount']} | Paid: {debts_df.loc[x, 'Paid Amount']}")
        
        curr_paid = float(debts_df.loc[sel_debt_idx, "Paid Amount"])
        tot_amt = float(debts_df.loc[sel_debt_idx, "Total Amount"])
        add_paid = st.sidebar.number_input("Add Settlement / Payment Amount (LKR)", min_value=0.0, max_value=tot_amt - curr_paid if tot_amt >= curr_paid else 0.0, step=100.0)
        settle_acc = st.sidebar.selectbox("Account used for Settlement/Receipt", accounts_df["Account Name"].tolist(), key="settle_acc")
        
        col_d1, col_d2 = st.sidebar.columns(2)
        if col_d1.button("Update Paid Status"):
            if add_paid > 0:
                debts_df.loc[sel_debt_idx, "Paid Amount"] += add_paid
                d_type = debts_df.loc[sel_debt_idx, "Type"]
                
                if d_type == "Borrowing (Nayata Gatta)":
                    accounts_df.loc[accounts_df["Account Name"] == settle_acc, "Balance (LKR)"] -= add_paid
                else:
                    accounts_df.loc[accounts_df["Account Name"] == settle_acc, "Balance (LKR)"] += add_paid
                
                save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after debt settlement")
                save_csv_to_github(debts_df, "data/debts.csv", "Update debt paid amount")
                st.sidebar.success(f"Successfully updated debt payment of LKR {add_paid:,.2f}!")
                st.rerun()
                
        if col_d2.button("Delete Debt Record"):
            d_type = debts_df.loc[sel_debt_idx, "Type"]
            d_tot = float(debts_df.loc[sel_debt_idx, "Total Amount"])
            d_paid = float(debts_df.loc[sel_debt_idx, "Paid Amount"])
            d_acc = debts_df.loc[sel_debt_idx, "Account"]
            
            # Reverse initial net impact & settlements on account balance
            # Borrowing: initially balance increased by (d_tot - d_paid). If deleted, decrease balance by that amount. Also if any paid amounts were settled from accounts, revert them.
            net_initial_impact = d_tot - d_paid
            if d_type == "Borrowing (Nayata Gatta)":
                if d_acc in accounts_df["Account Name"].values:
                    accounts_df.loc[accounts_df["Account Name"] == d_acc, "Balance (LKR)"] -= net_initial_impact
                # Revert paid amounts if they were deducted from settle accounts (simplified: add back total paid if settled)
                if d_paid > 0 and d_acc in accounts_df["Account Name"].values:
                    accounts_df.loc[accounts_df["Account Name"] == d_acc, "Balance (LKR)"] += d_paid
            else: # Lending
                if d_acc in accounts_df["Account Name"].values:
                    accounts_df.loc[accounts_df["Account Name"] == d_acc, "Balance (LKR)"] += net_initial_impact
                if d_paid > 0 and d_acc in accounts_df["Account Name"].values:
                    accounts_df.loc[accounts_df["Account Name"] == d_acc, "Balance (LKR)"] -= d_paid
            
            debts_df = debts_df.drop(sel_debt_idx).reset_index(drop=True)
            save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after debt deletion")
            save_csv_to_github(debts_df, "data/debts.csv", "Delete debt record")
            st.sidebar.success("Debt record deleted and balances reverted!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🏦 Manage Accounts & Wallets")
    new_acc = st.sidebar.text_input("New Account Name")
    init_bal = st.sidebar.number_input("Initial Balance", min_value=0.0, step=1000.0)
    if st.sidebar.button("Add Account"):
        if new_acc and new_acc not in accounts_df["Account Name"].values:
            accounts_df = pd.concat([accounts_df, pd.DataFrame({"Account Name": [new_acc], "Balance (LKR)": [init_bal]})], ignore_index=True)
            save_csv_to_github(accounts_df, "data/accounts.csv", "Add new account")
            st.sidebar.success("Account added!")
            st.rerun()

    if not accounts_df.empty:
        st.sidebar.markdown("##### Edit / Delete Existing Account")
        sel_acc_edit = st.sidebar.selectbox("Select Account", accounts_df["Account Name"].tolist(), key="sel_acc_edit")
        curr_acc_bal = float(accounts_df.loc[accounts_df["Account Name"] == sel_acc_edit, "Balance (LKR)"].values[0])
        
        new_acc_name = st.sidebar.text_input("Rename Account", value=sel_acc_edit, key="ren_acc")
        new_acc_bal = st.sidebar.number_input("Modify Balance", value=curr_acc_bal, step=100.0, key="mod_bal")
        
        col_ac1, col_ac2 = st.sidebar.columns(2)
        if col_ac1.button("Update Account"):
            if new_acc_name and (new_acc_name == sel_acc_edit or new_acc_name not in accounts_df["Account Name"].values):
                accounts_df.loc[accounts_df["Account Name"] == sel_acc_edit, "Account Name"] = new_acc_name
                accounts_df.loc[accounts_df["Account Name"] == new_acc_name, "Balance (LKR)"] = new_acc_bal
                save_csv_to_github(accounts_df, "data/accounts.csv", "Update account details")
                st.sidebar.success("Account updated successfully!")
                st.rerun()
            else:
                st.sidebar.error("Invalid name or already exists.")
                
        if col_ac2.button("Delete Account"):
            if len(accounts_df) > 1:
                accounts_df = accounts_df[accounts_df["Account Name"] != sel_acc_edit].reset_index(drop=True)
                save_csv_to_github(accounts_df, "data/accounts.csv", "Delete account")
                st.sidebar.success(f"Deleted {sel_acc_edit}!")
                st.rerun()
            else:
                st.sidebar.error("You must keep at least one account!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Manage Categories")
    new_cat = st.sidebar.text_input("New Category Name")
    if st.sidebar.button("Add Category"):
        if new_cat and new_cat not in categories_df["Category"].values:
            categories_df = pd.concat([categories_df, pd.DataFrame({"Category": [new_cat]})], ignore_index=True)
            save_csv_to_github(categories_df, "data/categories.csv", "Add category")
            st.sidebar.success("Category added!")
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
debt_paid = st.sidebar.number_input("Already Paid / Settled Amount", min_value=0.0, step=1000.0)
debt_account = st.sidebar.selectbox("Affected Account/Wallet", accounts_df["Account Name"].tolist(), key="debt_acc")
debt_note = st.sidebar.text_input("Note / Description")

if st.sidebar.button("Add Debt / Lending"):
    if person_name and debt_total > 0:
        new_debt = pd.DataFrame({
            "Type": [debt_type],
            "Person/Entity": [person_name],
            "Total Amount": [debt_total],
            "Paid Amount": [debt_paid],
            "Account": [debt_account],
            "Note": [debt_note]
        })
        debts_df = pd.concat([debts_df, new_debt], ignore_index=True)
        save_csv_to_github(debts_df, "data/debts.csv", "Add debt or lending")
        
        net_initial_impact = debt_total - debt_paid
        if debt_type == "Borrowing (Nayata Gatta)":
            accounts_df.loc[accounts_df["Account Name"] == debt_account, "Balance (LKR)"] += net_initial_impact
        else:
            accounts_df.loc[accounts_df["Account Name"] == debt_account, "Balance (LKR)"] -= net_initial_impact
            
        save_csv_to_github(accounts_df, "data/accounts.csv", "Update accounts after debt addition")
        
        st.sidebar.success("Successfully recorded and account balance updated!")
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
    net_debt_pos = rem_lend - rem_borrow  # Lending (+) minus Borrowing (-)
    col4.metric("Net Debt Position", f"LKR {net_debt_pos:,.2f}", delta=f"Lending: +{rem_lend:,.2f} | Borrowing: -{rem_borrow:,.2f}")
else:
    col4.metric("Net Debt Position", "LKR 0.00")

st.markdown("---")
st.subheader("🏦 Bank Accounts & Cash Wallets Status")
st.dataframe(accounts_df, use_container_width=True)

# --- ALL TRANSACTIONS HISTORY & DOWNLOAD ---
st.markdown("---")
st.subheader("📜 All Transactions History (Incomes (+), Expenses (-), Transfers, Debts)")

all_tx_list = []
if not incomes_df.empty:
    for _, r in incomes_df.iterrows():
        all_tx_list.append({"Date": r["Date"], "Type": "Income", "Details": r["Income Source"], "Amount (LKR)": f"+ {r['Amount (LKR)']:,.2f}", "RawAmount": r["Amount (LKR)"], "Account/Method": r["Account"]})
if not expenses_df.empty:
    for _, r in expenses_df.iterrows():
        all_tx_list.append({"Date": r["Date"], "Type": "Expense", "Details": f"{r['Description']} ({r['Category']})", "Amount (LKR)": f"- {r['Amount (LKR)']:,.2f}", "RawAmount": -r["Amount (LKR)"], "Account/Method": r["Payment Method"]})
if not transfers_df.empty:
    for _, r in transfers_df.iterrows():
        all_tx_list.append({"Date": r["Date"], "Type": "Transfer", "Details": f"From {r['From']} To {r['To']}", "Amount (LKR)": f"{r['Amount (LKR)']:,.2f}", "RawAmount": 0.0, "Account/Method": f"{r['From']} -> {r['To']}"})
if not debts_df.empty:
    for _, r in debts_df.iterrows():
        if r["Type"] == "Lending (Nayata Dunna)":
            amt_str = f"+ {r['Total Amount']:,.2f} (Lending)"
            raw_amt = r["Total Amount"]
        else:
            amt_str = f"- {r['Total Amount']:,.2f} (Borrowing)"
            raw_amt = -r["Total Amount"]
        all_tx_list.append({"Date": str(pd.Timestamp.today().strftime("%Y-%m-%d")), "Type": r["Type"], "Details": f"{r['Person/Entity']} - {r['Note']}", "Amount (LKR)": amt_str, "RawAmount": raw_amt, "Account/Method": r["Account"]})

if all_tx_list:
    all_tx_df = pd.DataFrame(all_tx_list)
    all_tx_df = all_tx_df.sort_values(by="Date", ascending=False).reset_index(drop=True)
    
    # Display table without raw sorting column
    st.dataframe(all_tx_df[["Date", "Type", "Details", "Amount (LKR)", "Account/Method"]], use_container_width=True)
    st.download_button("📥 Download All Transactions CSV", all_tx_df[["Date", "Type", "Details", "Amount (LKR)", "Account/Method"]].to_csv(index=False), "all_transactions.csv", "text/csv")
else:
    st.info("No transactions recorded yet.")

# --- REPORTS WITH CUSTOM DATE RANGE ---
st.markdown("---")
st.subheader("📊 Advanced Financial Reports (Custom Date Range & Filters)")

if not expenses_df.empty or not incomes_df.empty:
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
