from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account
import pandas as pd

# Cấu hình
KEY_FILE_LOCATION = 'thu-vien-phap-dang-9f3e5c10263e.json'
PROPERTY_ID = '517638323'  # Chỉ số, không có "properties/"

def initialize_analytics_client():
    """Khởi tạo GA4 client với service account"""
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE_LOCATION
    )
    client = BetaAnalyticsDataClient(credentials=credentials)
    return client

def get_basic_report(client, property_id, start_date='30daysAgo', end_date='today'):
    """
    Lấy báo cáo cơ bản: users, sessions, pageviews theo ngày
    """
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    
    response = client.run_report(request)
    return response

def response_to_dataframe(response):
    """Chuyển response thành pandas DataFrame"""
    rows = []
    for row in response.rows:
        row_dict = {}
        # Lấy dimensions
        for i, dimension_value in enumerate(row.dimension_values):
            dimension_name = response.dimension_headers[i].name
            row_dict[dimension_name] = dimension_value.value
        
        # Lấy metrics
        for i, metric_value in enumerate(row.metric_values):
            metric_name = response.metric_headers[i].name
            row_dict[metric_name] = metric_value.value
        
        rows.append(row_dict)
    
    return pd.DataFrame(rows)

# Sử dụng
if __name__ == "__main__":
    # Khởi tạo client
    client = initialize_analytics_client()
    
    # Lấy dữ liệu 30 ngày gần nhất
    response = get_basic_report(client, PROPERTY_ID)
    
    # Chuyển sang DataFrame
    df = response_to_dataframe(response)
    
    # Hiển thị
    print(df)
    
    # Lưu ra CSV
    df.to_csv('ga4_data.csv', index=False)
    print("\nĐã lưu dữ liệu vào ga4_data.csv")