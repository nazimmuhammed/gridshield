import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report

# Load the dataset
df = pd.read_csv("data/grid_stability.csv")

print("=" * 60)
print("BASIC EDA")
print("=" * 60)
print(f"Shape: {df.shape}")
print(f"\nColumns: {list(df.columns)}")
print(f"\nClass balance:\n{df['stabf'].value_counts()}")
print(f"\nMissing values: {df.isnull().sum().sum()} total")
print(f"\nSummary stats:\n{df.describe()}")

# Prepare features/target
X = df.drop(columns=["stab", "stabf"])   # stab is a near-leak of stabf, exclude it
y = (df["stabf"] == "unstable").astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print("\n" + "=" * 60)
print("BASELINE MODELS")
print("=" * 60)

# Logistic Regression baseline
lr = LogisticRegression(max_iter=1000)
lr.fit(X_train, y_train)
lr_proba = lr.predict_proba(X_test)[:, 1]
print(f"\nLogistic Regression AUC-ROC: {roc_auc_score(y_test, lr_proba):.4f}")

# Random Forest (stronger baseline)
rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
rf_proba = rf.predict_proba(X_test)[:, 1]
print(f"Random Forest AUC-ROC: {roc_auc_score(y_test, rf_proba):.4f}")

print("\nClassification Report (Random Forest):")
print(classification_report(y_test, rf.predict(X_test)))

print("\nFeature Importances:")
importances = pd.Series(rf.feature_importances_, index=X.columns)
print(importances.sort_values(ascending=False))