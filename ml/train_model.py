"""
Random Forest Model Training Script
Trains a behavior classification model using synthetic data
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.constants import BehaviorLabel, Config


def generate_synthetic_data(n_samples_per_class: int = 500) -> pd.DataFrame:
    """
    Generate synthetic training data for behavior classification
    
    Args:
        n_samples_per_class: Number of samples to generate per behavior class
        
    Returns:
        DataFrame with columns: pitch, yaw, roll, eye_ratio, mar, label
    """
    data = []
    
    # Class 0: NORMAL - centered head, looking forward
    for _ in range(n_samples_per_class):
        pitch = np.random.normal(0, 5)  # Centered with small variance
        yaw = np.random.normal(0, 5)
        roll = np.random.normal(0, 3)
        eye_ratio = np.random.normal(0.5, 0.05)  # Looking center
        mar = np.random.uniform(0.1, 0.3)  # Mouth closed
        data.append([pitch, yaw, roll, eye_ratio, mar, BehaviorLabel.NORMAL])
    
    # Class 1: LOOKING_LEFT - yaw negative
    for _ in range(n_samples_per_class):
        pitch = np.random.normal(0, 8)
        yaw = np.random.uniform(-60, -20)  # Looking left
        roll = np.random.normal(0, 5)
        eye_ratio = np.random.normal(0.3, 0.1)  # Eyes shifted left
        mar = np.random.uniform(0.1, 0.3)
        data.append([pitch, yaw, roll, eye_ratio, mar, BehaviorLabel.LOOKING_LEFT])
    
    # Class 2: LOOKING_RIGHT - yaw positive
    for _ in range(n_samples_per_class):
        pitch = np.random.normal(0, 8)
        yaw = np.random.uniform(20, 60)  # Looking right
        roll = np.random.normal(0, 5)
        eye_ratio = np.random.normal(0.7, 0.1)  # Eyes shifted right
        mar = np.random.uniform(0.1, 0.3)
        data.append([pitch, yaw, roll, eye_ratio, mar, BehaviorLabel.LOOKING_RIGHT])
    
    # Class 3: HEAD_DOWN - pitch positive
    for _ in range(n_samples_per_class):
        pitch = np.random.uniform(25, 60)  # Head down
        yaw = np.random.normal(0, 10)
        roll = np.random.normal(0, 5)
        eye_ratio = np.random.normal(0.5, 0.1)
        mar = np.random.uniform(0.1, 0.3)
        data.append([pitch, yaw, roll, eye_ratio, mar, BehaviorLabel.HEAD_DOWN])
    
    # Create DataFrame
    df = pd.DataFrame(
        data, 
        columns=['pitch', 'yaw', 'roll', 'eye_ratio', 'mar', 'label']
    )
    
    return df


def train_model(
    data: pd.DataFrame, 
    save_path: str,
    test_size: float = 0.2,
    random_state: int = 42
) -> RandomForestClassifier:
    """
    Train Random Forest classifier
    
    Args:
        data: Training data DataFrame
        save_path: Path to save trained model
        test_size: Proportion of data for testing
        random_state: Random seed
        
    Returns:
        Trained model
    """
    print("=" * 60)
    print("Training Random Forest Behavior Classifier")
    print("=" * 60)
    
    # Separate features and labels
    X = data[['pitch', 'yaw', 'roll', 'eye_ratio', 'mar']].values
    y = data['label'].values
    
    print(f"\n📊 Dataset Info:")
    print(f"  Total samples: {len(data)}")
    print(f"  Features: {X.shape[1]}")
    print(f"  Classes: {len(np.unique(y))}")
    print(f"\n  Class distribution:")
    for label in np.unique(y):
        count = np.sum(y == label)
        print(f"    {label}: {count} samples")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    print(f"\n📈 Training set: {len(X_train)} samples")
    print(f"📉 Test set: {len(X_test)} samples")
    
    # Train Random Forest
    print("\n⏳ Training Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1  # Use all CPU cores
    )
    
    model.fit(X_train, y_train)
    print("✅ Training completed!")
    
    # Evaluate
    print("\n📊 Model Evaluation:")
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n  Accuracy: {accuracy:.2%}")
    
    print("\n  Classification Report:")
    class_names = ['NORMAL', 'LOOKING_LEFT', 'LOOKING_RIGHT', 'HEAD_DOWN']
    print(classification_report(y_test, y_pred, target_names=class_names))
    
    print("\n  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    # Feature importance
    print("\n  Feature Importance:")
    feature_names = ['pitch', 'yaw', 'roll', 'eye_ratio', 'mar']
    importances = model.feature_importances_
    for name, importance in zip(feature_names, importances):
        print(f"    {name}: {importance:.4f}")
    
    # Save model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(model, save_path)
    print(f"\n💾 Model saved to: {save_path}")
    
    return model


def load_real_data(data_dir: str) -> pd.DataFrame:
    """
    Load real collected data from CSV files in a directory
    
    Args:
        data_dir: Directory containing CSV files
        
    Returns:
        Combined DataFrame from all CSV files
    """
    import glob
    
    csv_files = glob.glob(os.path.join(data_dir, "collected_data_*.csv"))
    
    if not csv_files:
        print(f"  No collected data files found in {data_dir}")
        return None
    
    dataframes = []
    for csv_file in csv_files:
        print(f"  Loading: {csv_file}")
        df = pd.read_csv(csv_file)
        dataframes.append(df)
    
    combined = pd.concat(dataframes, ignore_index=True)
    print(f"  Loaded {len(combined)} samples from {len(csv_files)} file(s)")
    
    return combined


def main():
    """Main training pipeline with support for real data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train FocusGuard Behavior Classifier")
    parser.add_argument("--data", type=str, default=None,
                        help="Directory containing collected CSV data files")
    parser.add_argument("--synthetic", type=int, default=500,
                        help="Samples per class for synthetic data (default: 500)")
    parser.add_argument("--combine", action="store_true",
                        help="Combine real data with synthetic data")
    args = parser.parse_args()
    
    print("\n🚀 FocusGuard Behavior Classifier Training\n")
    
    data = None
    
    # Try to load real data
    if args.data:
        print("📦 Loading real collected data...")
        data = load_real_data(args.data)
        
        if data is not None and args.combine:
            print("\n📦 Generating synthetic data to combine...")
            synthetic = generate_synthetic_data(n_samples_per_class=args.synthetic)
            data = pd.concat([data, synthetic], ignore_index=True)
            print(f"✅ Combined dataset: {len(data)} samples")
    
    # Fallback to synthetic data
    if data is None or len(data) == 0:
        print("📦 Generating synthetic training data...")
        data = generate_synthetic_data(n_samples_per_class=args.synthetic)
    
    # Save training data for reference
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    data_path = os.path.join(data_dir, 'training_data.csv')
    data.to_csv(data_path, index=False)
    print(f"✅ Training data saved to: {data_path}")
    
    # Train model
    model_path = os.path.join(os.path.dirname(__file__), 'models/behavior_model.pkl')
    model = train_model(data, model_path)
    
    print("\n" + "=" * 60)
    print("✅ Training completed successfully!")
    print("=" * 60)
    print(f"\nUsage:")
    print(f"  from client.ai_engine.classifier import BehaviorClassifier")
    print(f"  classifier = BehaviorClassifier()")
    print("\n")



if __name__ == "__main__":
    main()
