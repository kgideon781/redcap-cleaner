import pandas as pd
import streamlit as st
import io
import os


def clean_and_align_redcap_data(df, profile_pattern='profile', period_pattern='period',
                                id_col='Record ID', event_col='Event Name'):
    """
    Clean REDCap data to keep only records with both profile and period events,
    aligning period data as subsequent rows under each profile (profile first),
    excluding blank periods.
    """
    # Convert event names to lowercase for case-insensitive matching
    df[event_col] = df[event_col].str.lower()

    # Separate profile and period records
    profile_df = df[df[event_col].str.contains(profile_pattern, na=False)].copy()
    period_df = df[df[event_col].str.contains(period_pattern, na=False)].copy()

    # Define key publication fields to check for blank periods
    key_fields = ['Research output title', 'APA reference citation of Publication',
                  'Date of publication', 'Publication Year', 'Name of the publishing Journal']

    # Filter out blank period rows (where all key fields are NaN or empty)
    period_df = period_df.dropna(subset=key_fields, how='all')
    period_df = period_df[~period_df[key_fields].apply(lambda x: x.str.strip() == '').all(axis=1)]

    # Get Record IDs that have both profile and period events
    profile_ids = set(profile_df[id_col])
    period_ids = set(period_df[id_col])
    valid_ids = profile_ids.intersection(period_ids)  # Keep only IDs with both

    # Filter to keep only records with both profile and non-blank period events
    profile_df = profile_df[profile_df[id_col].isin(valid_ids)]
    period_df = period_df[period_df[id_col].isin(valid_ids)]

    # Concatenate profile and period data vertically
    result_df = pd.concat([profile_df, period_df], ignore_index=True)

    # Create a sorting key to ensure Profile comes first
    result_df['Sort_Key'] = result_df[event_col].apply(lambda x: 0 if profile_pattern in x else 1)

    # Sort by Record ID, then Sort_Key (profile first), then Repeat Instance
    result_df = result_df.sort_values(by=[id_col, 'Sort_Key', 'Repeat Instance'])

    # Drop the temporary Sort_Key column
    result_df = result_df.drop(columns=['Sort_Key'])

    # Reset index for clean output
    result_df = result_df.reset_index(drop=True)

    return result_df


# Streamlit app
st.title("REDCap Data Cleaner")
st.write("Upload your REDCap CSV file to clean it. The processed file will be available for download.")

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        # Read the uploaded CSV
        df = pd.read_csv(uploaded_file)
        st.write(f"Original records: {len(df)}")

        # Process the data
        cleaned_df = clean_and_align_redcap_data(df)

        if cleaned_df is not None and not cleaned_df.empty:
            # Display stats
            st.write(f"Filtered records: {len(cleaned_df)}")
            st.write(f"Unique Record IDs: {cleaned_df['Record ID'].nunique()}")

            # Convert DataFrame to CSV for download
            csv_buffer = io.StringIO()
            cleaned_df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode('utf-8')

            # Download button
            st.download_button(
                label="Download Cleaned CSV",
                data=csv_bytes,
                file_name=f"cleaned_{uploaded_file.name}",
                mime="text/csv"
            )
        else:
            st.error("No valid data to process after cleaning.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")