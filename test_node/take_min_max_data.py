import pandas as pd

# Load raw data
raw_data = pd.read_csv(r'Datatest/cyclingLabel.csv')
preprocess_data = raw_data.copy()
preprocess_data.drop(columns=["date", "t", "encoder_count", "level", "period", "degree", "turn", "push_leg", "mode"], inplace=True)
min_max_list = []
for col in preprocess_data.columns:
    if col != 'phase':  # Exclude the 'phase' column
      if preprocess_data[col].dtype in ['int64', 'float64']:  # Check if column is numeric
          min_val = preprocess_data[col].min()
          max_val = preprocess_data[col].max()
          min_max_list.append((min_val, max_val))
      else:
          min_max_list.append(('Not applicable', 'Not applicable')) # or handle non-numeric columns as needed

# Save min_max_list to a CSV file
min_max_df = pd.DataFrame(min_max_list, columns=['min', 'max'])
min_max_df.to_csv(r'min_max_values.csv', index=False)

# # Load min_max_list from the CSV file
# loaded_min_max_df = pd.read_csv('/min_max_values.csv')
# loaded_min_max_list = list(loaded_min_max_df.itertuples(index=False, name=None))