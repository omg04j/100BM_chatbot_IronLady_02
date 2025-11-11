"""
Admin Dashboard for 100BM AI Assistant Feedback
View and analyze user feedback with statistics and insights
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal, Feedback
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="100BM Feedback Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #C41E3A 0%, #8B1538 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Database session
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Load feedback data
@st.cache_data(ttl=60)
def load_feedback_data():
    db = get_db()
    feedback = db.query(Feedback).all()
    
    data = []
    for f in feedback:
        data.append({
            'id': f.id,
            'session_id': f.session_id,
            'message_id': f.message_id,
            'question': f.question,
            'answer': f.answer,
            'rating': f.rating,
            'timestamp': f.timestamp,
            'user_comment': f.user_comment
        })
    
    return pd.DataFrame(data) if data else pd.DataFrame()

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 100BM AI Assistant - Feedback Dashboard</h1>
    <p>Monitor and analyze chatbot performance through user feedback</p>
</div>
""", unsafe_allow_html=True)

# Load data
df = load_feedback_data()

if df.empty:
    st.info("📭 No feedback data available yet. Start chatting to see feedback!")
    st.stop()

# Calculate metrics
total_feedback = len(df)
positive_count = len(df[df['rating'] == 'positive'])
negative_count = len(df[df['rating'] == 'negative'])
positive_rate = (positive_count / total_feedback * 100) if total_feedback > 0 else 0

# Top metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📈 Total Feedback",
        value=total_feedback
    )

with col2:
    st.metric(
        label="👍 Positive",
        value=positive_count,
        delta=f"{positive_rate:.1f}%"
    )

with col3:
    st.metric(
        label="👎 Negative",
        value=negative_count,
        delta=f"{100-positive_rate:.1f}%"
    )

with col4:
    st.metric(
        label="✅ Satisfaction Rate",
        value=f"{positive_rate:.1f}%"
    )

st.divider()

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Feedback Distribution")
    fig = go.Figure(data=[go.Pie(
        labels=['Positive 👍', 'Negative 👎'],
        values=[positive_count, negative_count],
        hole=.4,
        marker_colors=['#4CAF50', '#f44336']
    )])
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📅 Feedback Over Time")
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_feedback = df.groupby('date').size().reset_index(name='count')
    
    fig = px.line(
        daily_feedback, 
        x='date', 
        y='count',
        markers=True,
        title="Daily Feedback Count"
    )
    fig.update_traces(line_color='#C41E3A')
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Filters
st.subheader("🔍 Filter Feedback")
col1, col2 = st.columns(2)

with col1:
    rating_filter = st.selectbox(
        "Rating",
        ["All", "Positive", "Negative"]
    )

with col2:
    days_filter = st.slider(
        "Last N Days",
        min_value=1,
        max_value=30,
        value=7
    )

# Apply filters
filtered_df = df.copy()

if rating_filter != "All":
    filtered_df = filtered_df[filtered_df['rating'] == rating_filter.lower()]

date_threshold = datetime.now() - timedelta(days=days_filter)
filtered_df['timestamp'] = pd.to_datetime(filtered_df['timestamp'])
filtered_df = filtered_df[filtered_df['timestamp'] >= date_threshold]

st.divider()

# Recent feedback table
st.subheader(f"📋 Recent Feedback ({len(filtered_df)} items)")

for idx, row in filtered_df.sort_values('timestamp', ascending=False).iterrows():
    with st.expander(
        f"{'👍' if row['rating'] == 'positive' else '👎'} {row['timestamp'].strftime('%Y-%m-%d %H:%M')} - {row['question'][:60]}..."
    ):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown(f"**Rating:** {'👍 Positive' if row['rating'] == 'positive' else '👎 Negative'}")
            st.markdown(f"**Time:** {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown(f"**Session:** `{row['session_id'][:20]}...`")
        
        with col2:
            st.markdown("**Question:**")
            st.info(row['question'])
            
            st.markdown("**Answer:**")
            st.success(row['answer'][:500] + "..." if len(row['answer']) > 500 else row['answer'])

st.divider()

# Export data
st.subheader("💾 Export Data")
col1, col2 = st.columns(2)

with col1:
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name=f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

with col2:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>100BM AI Assistant - Admin Dashboard | Iron Lady Leadership Program</p>
</div>
""", unsafe_allow_html=True)