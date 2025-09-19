import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Optional
import time

# Configure Streamlit page
st.set_page_config(
    page_title="GitHub PR Dashboard",
    page_icon="📊",
    layout="wide"
)

class GitHubPRAnalyzer:
    def __init__(self, token: Optional[str] = None):
        self.token = token.strip() if token else None
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'PR-Dashboard-App'
        }
        if self.token:
            # Use the standard GitHub token format
            self.headers['Authorization'] = f'token {self.token}'
    
    def _check_rate_limit_with_token(self) -> Dict:
        """Check rate limit status with current token to verify authentication"""
        try:
            response = requests.get("https://api.github.com/rate_limit", headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def fetch_pull_requests(_self, owner: str, repo: str, state: str = 'all') -> List[Dict]:
        """Fetch last 100 pull requests from GitHub API with caching and error handling"""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            'state': state,
            'per_page': 100,  # Always fetch only 100 PRs
            'sort': 'created',
            'direction': 'desc',
            'page': 1  # Only first page
        }
        
        max_retries = 3
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # If we have a token, verify it's working by checking rate limit
        if _self.token:
            rate_limit_info = _self._check_rate_limit_with_token()
            if rate_limit_info and 'rate' in rate_limit_info:
                remaining = rate_limit_info['rate']['remaining']
                limit = rate_limit_info['rate']['limit']
                st.info(f"✅ Token authenticated successfully! Rate limit: {remaining}/{limit}")
            else:
                # Try fallback to Bearer token format
                st.warning("Standard token format failed, trying Bearer token format...")
                _self.headers['Authorization'] = f'Bearer {_self.token}'
                rate_limit_info = _self._check_rate_limit_with_token()
                if rate_limit_info and 'rate' in rate_limit_info:
                    remaining = rate_limit_info['rate']['remaining']
                    limit = rate_limit_info['rate']['limit']
                    st.info(f"✅ Token authenticated with Bearer format! Rate limit: {remaining}/{limit}")
                else:
                    st.error("❌ Token authentication failed with both standard and Bearer formats. Please check your token.")
                    return []
        
        try:
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    status_text.text("Fetching last 100 PRs...")
                    progress_bar.progress(0.5)
                    
                    response = requests.get(url, headers=_self.headers, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        progress_bar.progress(1.0)
                        break
                    elif response.status_code == 403:
                        # Check if it's rate limit or other 403 error
                        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
                        rate_limit_reset = response.headers.get('X-RateLimit-Reset')
                        
                        if int(rate_limit_remaining) == 0:
                            if rate_limit_reset:
                                reset_time = datetime.fromtimestamp(int(rate_limit_reset))
                                if _self.token:
                                    st.error(f"Rate limit exceeded even with token! Resets at {reset_time.strftime('%H:%M:%S')}. Your token might be invalid or you've exceeded the authenticated rate limit.")
                                else:
                                    st.error(f"Rate limit exceeded. Resets at {reset_time.strftime('%H:%M:%S')}. Please add a GitHub token.")
                            else:
                                st.error("Rate limit exceeded. Please add a GitHub token or wait for reset.")
                        else:
                            st.error(f"Access forbidden (403). This might be a private repository or your token lacks permissions.")
                        return []
                    elif response.status_code == 404:
                        st.error(f"Repository '{owner}/{repo}' not found. This could mean:")
                        st.error("• The repository name is incorrect")
                        st.error("• The repository is private and your token lacks 'repo' scope")
                        st.error("• The repository doesn't exist or you don't have access")
                        if _self.token:
                            st.info("💡 For private repositories, ensure your token has the 'repo' scope (full control)")
                        else:
                            st.info("💡 If this is a private repository, you need a GitHub token with 'repo' scope")
                        return []
                    elif response.status_code == 401:
                        st.error("Invalid GitHub token. Please check your token.")
                        return []
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            st.warning(f"Request failed (attempt {retry_count}/{max_retries}). Retrying...")
                            time.sleep(2 ** retry_count)  # Exponential backoff
                        else:
                            st.error(f"Error fetching data: {response.status_code} - {response.text}")
                            return []
                
                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        st.warning(f"Request timeout (attempt {retry_count}/{max_retries}). Retrying...")
                        time.sleep(2 ** retry_count)
                    else:
                        st.error("Request timeout. Please try again later.")
                        return []
                
                except requests.exceptions.ConnectionError:
                    retry_count += 1
                    if retry_count < max_retries:
                        st.warning(f"Connection error (attempt {retry_count}/{max_retries}). Retrying...")
                        time.sleep(2 ** retry_count)
                    else:
                        st.error("Connection error. Please check your internet connection.")
                        return []
                
                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")
                    return []
            
            try:
                prs = response.json()
                if not prs:
                    st.warning("No pull requests found in this repository.")
                    return []
                return prs
            except ValueError:
                st.error("Invalid response format from GitHub API.")
                return []
        
        finally:
            progress_bar.empty()
            status_text.empty()
    
    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def process_pr_data(_self, prs: List[Dict]) -> pd.DataFrame:
        """Process PR data into a structured DataFrame with caching"""
        if not prs:
            return pd.DataFrame()
        
        processed_data = []
        
        try:
            for pr in prs:
                try:
                    # Calculate time to merge/close
                    created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                    
                    merged_at = None
                    closed_at = None
                    time_to_action = None
                    
                    if pr.get('merged_at'):
                        merged_at = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                        time_to_action = (merged_at - created_at).days
                    elif pr.get('closed_at'):
                        closed_at = datetime.fromisoformat(pr['closed_at'].replace('Z', '+00:00'))
                        time_to_action = (closed_at - created_at).days
                    
                    # Determine status
                    if pr.get('merged_at'):
                        status = "Merged"
                    elif pr.get('closed_at'):
                        status = "Closed"
                    else:
                        status = "Open"
                    
                    # Safely extract user information
                    author = pr.get('user', {}).get('login', 'Unknown') if pr.get('user') else 'Unknown'
                    
                    # Safely extract labels and assignees
                    labels = ', '.join([label.get('name', '') for label in pr.get('labels', []) if label.get('name')])
                    assignees = ', '.join([assignee.get('login', '') for assignee in pr.get('assignees', []) if assignee.get('login')])
                    
                    processed_data.append({
                        'PR No': pr.get('number', 0),
                        'PR Title': pr.get('title', 'No Title'),
                        'Created Date': created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Merged Date': merged_at.strftime('%Y-%m-%d %H:%M:%S') if merged_at else None,
                        'Closed Date': closed_at.strftime('%Y-%m-%d %H:%M:%S') if closed_at else None,
                        'Status': status,
                        'Link': pr.get('html_url', ''),
                        'Time to Merge/Close (days)': time_to_action,
                        'Author': author,
                        'Labels': labels,
                        'Assignees': assignees,
                        'Comments': pr.get('comments', 0),
                        'Additions': pr.get('additions', 0),
                        'Deletions': pr.get('deletions', 0),
                        'Changed Files': pr.get('changed_files', 0)
                    })
                
                except Exception as e:
                    st.warning(f"Error processing PR #{pr.get('number', 'unknown')}: {str(e)}")
                    continue
        
        except Exception as e:
            st.error(f"Error processing PR data: {str(e)}")
            return pd.DataFrame()
        
        return pd.DataFrame(processed_data)

def main():
    st.title("🔍 GitHub Pull Request Dashboard")
    st.markdown("Analyze and visualize pull request data from any GitHub repository")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # GitHub token input
    github_token = st.sidebar.text_input(
        "GitHub Personal Access Token (Optional)",
        type="password",
        help="Provide a token for higher rate limits and private repos"
    )
    
    # Repository input
    repo_url = st.sidebar.text_input(
        "Repository URL or Owner/Repo",
        placeholder="e.g., microsoft/vscode or https://github.com/microsoft/vscode"
    )
    
    # Parse repository information
    if repo_url:
        if repo_url.startswith('https://github.com/'):
            repo_path = repo_url.replace('https://github.com/', '').rstrip('/')
        else:
            repo_path = repo_url
        
        if '/' in repo_path:
            owner, repo = repo_path.split('/', 1)
            
            if st.sidebar.button("Fetch PR Data", type="primary"):
                with st.spinner("Fetching pull request data..."):
                    analyzer = GitHubPRAnalyzer(github_token if github_token else None)
                    prs = analyzer.fetch_pull_requests(owner, repo)
                    
                    if prs:
                        df = analyzer.process_pr_data(prs)
                        st.session_state['pr_data'] = df
                        st.session_state['repo_info'] = f"{owner}/{repo}"
                        st.success(f"Successfully fetched {len(df)} pull requests!")
                    else:
                        st.error("No pull requests found or error occurred.")
    
    # Display data if available
    if 'pr_data' in st.session_state:
        df = st.session_state['pr_data']
        repo_info = st.session_state['repo_info']
        
        st.header(f"📊 Pull Request Analysis for {repo_info}")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total PRs", len(df))
        
        with col2:
            merged_count = len(df[df['Status'] == 'Merged'])
            st.metric("Merged PRs", merged_count)
        
        with col3:
            open_count = len(df[df['Status'] == 'Open'])
            st.metric("Open PRs", open_count)
        
        with col4:
            avg_time = df[df['Time to Merge/Close (days)'].notna()]['Time to Merge/Close (days)'].mean()
            st.metric("Avg Time to Close", f"{avg_time:.1f} days" if not pd.isna(avg_time) else "N/A")
        
        # Filters
        st.subheader("🔍 Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                options=df['Status'].unique(),
                default=df['Status'].unique()
            )
        
        with col2:
            authors = df['Author'].unique()
            author_filter = st.multiselect(
                "Authors",
                options=authors,
                default=authors[:10] if len(authors) > 10 else authors
            )
        
        with col3:
            date_range = st.date_input(
                "Date Range",
                value=[],
                help="Filter by creation date"
            )
        
        # Apply filters
        filtered_df = df[
            (df['Status'].isin(status_filter)) &
            (df['Author'].isin(author_filter))
        ]
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df['Created Date Parsed'] = pd.to_datetime(filtered_df['Created Date'])
            filtered_df = filtered_df[
                (filtered_df['Created Date Parsed'].dt.date >= start_date) &
                (filtered_df['Created Date Parsed'].dt.date <= end_date)
            ]
        
        # Create tabs for better organization
        tab1, tab2, tab3 = st.tabs(["📋 Data Table", "📈 Visualizations", "📊 Advanced Analytics"])
        
        with tab1:
            st.subheader("📋 Pull Request Data")
            
            # Display columns selection
            display_columns = st.multiselect(
                "Select columns to display",
                options=df.columns.tolist(),
                default=['PR No', 'PR Title', 'Author', 'Created Date', 'Merged Date', 'Closed Date', 'Status', 'Link', 'Time to Merge/Close (days)']
            )
            
            if display_columns:
                # Make links clickable
                display_df = filtered_df[display_columns].copy()
                if 'Link' in display_columns:
                    display_df['Link'] = display_df['Link'].apply(lambda x: f'<a href="{x}" target="_blank">View PR</a>')
                
                st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # Download button
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"{repo_info.replace('/', '_')}_pr_data.csv",
                    mime="text/csv"
                )
        
        with tab2:
            st.subheader("📈 Pull Request Visualizations")
            
            # PR Status Distribution
            col1, col2 = st.columns(2)
            
            with col1:
                status_counts = filtered_df['Status'].value_counts()
                fig_pie = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="PR Status Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Time to merge/close histogram
                time_data = filtered_df[filtered_df['Time to Merge/Close (days)'].notna()]
                if not time_data.empty:
                    fig_hist = px.histogram(
                        time_data,
                        x='Time to Merge/Close (days)',
                        title="Time to Merge/Close Distribution",
                        nbins=20,
                        color_discrete_sequence=['#1f77b4']
                    )
                    fig_hist.update_layout(showlegend=False)
                    st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.info("No time data available for closed/merged PRs")
            
            # PRs over time
            if not filtered_df.empty:
                filtered_df['Created Date Parsed'] = pd.to_datetime(filtered_df['Created Date'])
                monthly_prs = filtered_df.groupby(filtered_df['Created Date Parsed'].dt.to_period('M')).size()
                
                fig_timeline = px.line(
                    x=monthly_prs.index.astype(str),
                    y=monthly_prs.values,
                    title="Pull Requests Created Over Time",
                    labels={'x': 'Month', 'y': 'Number of PRs'},
                    markers=True
                )
                fig_timeline.update_traces(line_color='#2E86AB', marker_color='#A23B72')
                st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Top contributors
            if 'Author' in filtered_df.columns:
                top_authors = filtered_df['Author'].value_counts().head(10)
                fig_authors = px.bar(
                    x=top_authors.values,
                    y=top_authors.index,
                    orientation='h',
                    title="Top Contributors",
                    labels={'x': 'Number of PRs', 'y': 'Author'},
                    color=top_authors.values,
                    color_continuous_scale='viridis'
                )
                fig_authors.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_authors, use_container_width=True)
        
        with tab3:
            st.subheader("📊 Advanced Analytics")
            
            # PR Size Analysis
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Additions' in filtered_df.columns and 'Deletions' in filtered_df.columns:
                    # Calculate PR size (total changes)
                    filtered_df['Total Changes'] = filtered_df['Additions'] + filtered_df['Deletions']
                    size_data = filtered_df[filtered_df['Total Changes'] > 0]
                    
                    if not size_data.empty:
                        fig_size = px.scatter(
                            size_data,
                            x='Additions',
                            y='Deletions',
                            size='Total Changes',
                            color='Status',
                            title="PR Size Analysis (Additions vs Deletions)",
                            hover_data=['PR No', 'PR Title', 'Author']
                        )
                        st.plotly_chart(fig_size, use_container_width=True)
                    else:
                        st.info("No code change data available")
                else:
                    st.info("Code change metrics not available")
            
            with col2:
                # Comments vs Time to Close
                if 'Comments' in filtered_df.columns:
                    comment_time_data = filtered_df[
                        (filtered_df['Time to Merge/Close (days)'].notna()) & 
                        (filtered_df['Comments'] >= 0)
                    ]
                    
                    if not comment_time_data.empty:
                        fig_comments = px.scatter(
                            comment_time_data,
                            x='Comments',
                            y='Time to Merge/Close (days)',
                            color='Status',
                            title="Comments vs Time to Close",
                            hover_data=['PR No', 'PR Title', 'Author']
                        )
                        st.plotly_chart(fig_comments, use_container_width=True)
                    else:
                        st.info("No comment/time correlation data available")
                else:
                    st.info("Comment data not available")
            
            # Author Activity Heatmap
            if not filtered_df.empty and 'Author' in filtered_df.columns:
                filtered_df['Created Date Parsed'] = pd.to_datetime(filtered_df['Created Date'])
                filtered_df['Month'] = filtered_df['Created Date Parsed'].dt.to_period('M').astype(str)
                
                # Create author-month matrix
                author_month = filtered_df.groupby(['Author', 'Month']).size().reset_index(name='PRs')
                author_month_pivot = author_month.pivot(index='Author', columns='Month', values='PRs').fillna(0)
                
                if not author_month_pivot.empty and len(author_month_pivot.columns) > 1:
                    fig_heatmap = px.imshow(
                        author_month_pivot.values,
                        x=author_month_pivot.columns,
                        y=author_month_pivot.index,
                        title="Author Activity Heatmap",
                        labels={'x': 'Month', 'y': 'Author', 'color': 'PRs'},
                        color_continuous_scale='Blues'
                    )
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                else:
                    st.info("Not enough data for activity heatmap")
            
            # PR Labels Analysis
            if 'Labels' in filtered_df.columns:
                # Extract and count all labels
                all_labels = []
                for labels_str in filtered_df['Labels'].dropna():
                    if labels_str.strip():
                        labels_list = [label.strip() for label in labels_str.split(',')]
                        all_labels.extend(labels_list)
                
                if all_labels:
                    label_counts = pd.Series(all_labels).value_counts().head(15)
                    
                    fig_labels = px.bar(
                        x=label_counts.values,
                        y=label_counts.index,
                        orientation='h',
                        title="Most Common PR Labels",
                        labels={'x': 'Count', 'y': 'Label'},
                        color=label_counts.values,
                        color_continuous_scale='plasma'
                    )
                    fig_labels.update_layout(showlegend=False, coloraxis_showscale=False)
                    st.plotly_chart(fig_labels, use_container_width=True)
                else:
                    st.info("No label data available")
            
            # Summary Statistics
            st.subheader("📈 Summary Statistics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**PR Status Summary:**")
                status_summary = filtered_df['Status'].value_counts()
                for status, count in status_summary.items():
                    percentage = (count / len(filtered_df)) * 100
                    st.write(f"• {status}: {count} ({percentage:.1f}%)")
            
            with col2:
                if 'Time to Merge/Close (days)' in filtered_df.columns:
                    time_data = filtered_df['Time to Merge/Close (days)'].dropna()
                    if not time_data.empty:
                        st.write("**Time to Close Statistics:**")
                        st.write(f"• Average: {time_data.mean():.1f} days")
                        st.write(f"• Median: {time_data.median():.1f} days")
                        st.write(f"• Min: {time_data.min():.0f} days")
                        st.write(f"• Max: {time_data.max():.0f} days")
                    else:
                        st.write("**Time to Close Statistics:**")
                        st.write("No time data available")
    
    else:
        st.info("👆 Enter a repository URL in the sidebar and click 'Fetch PR Data' to get started!")
        
        # Rate limit warning
        st.warning("⚠️ **Important**: Without a GitHub token, you're limited to 60 API requests per hour. For better performance and to avoid rate limits, please add a GitHub Personal Access Token in the sidebar.")
        
        # Example usage
        st.subheader("📖 How to use:")
        st.markdown("""
        1. **Recommended**: Enter your GitHub Personal Access Token for higher rate limits (5000/hour vs 60/hour)
        2. Enter a repository URL or owner/repo format (e.g., `microsoft/vscode`)
        3. Click "Fetch PR Data" to analyze the repository
        4. Use filters to refine your analysis
        5. Download the data as CSV for further analysis
        
        **Example repositories to try:**
        - `microsoft/vscode`
        - `facebook/react`
        - `tensorflow/tensorflow`
        - `kubernetes/kubernetes`
        """)
        
        # GitHub token instructions
        st.subheader("🔑 How to get a GitHub Personal Access Token:")
        st.markdown("""
        1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
        2. Click "Generate new token" → "Generate new token (classic)"
        3. Give it a name (e.g., "PR Dashboard")
        4. Select expiration (30 days recommended for testing)
        5. **⚠️ IMPORTANT: Select these scopes/permissions:**
           - ✅ **`public_repo`** - Access public repositories
           - ✅ **`repo:status`** - Access commit status
           - OR ✅ **`repo`** - Full control (if you need private repos)
        6. Click "Generate token"
        7. Copy the token and paste it in the sidebar
        
        **Note**: The token is only stored in your browser session and is not saved anywhere.
        
        **🚨 Common 403 Error Fix**: If you get "Access forbidden", your token needs the `public_repo` or `repo:status` scope!
        """)
        
        # Rate limit status
        st.subheader("📊 Current Rate Limit Status:")
        if st.button("Check Rate Limit"):
            try:
                response = requests.get("https://api.github.com/rate_limit")
                if response.status_code == 200:
                    rate_data = response.json()
                    core_limit = rate_data['rate']
                    remaining = core_limit['remaining']
                    limit = core_limit['limit']
                    reset_time = datetime.fromtimestamp(core_limit['reset'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Remaining Requests", remaining)
                    with col2:
                        st.metric("Total Limit", limit)
                    with col3:
                        st.metric("Resets At", reset_time.strftime("%H:%M:%S"))
                    
                    if remaining < 10:
                        st.error("⚠️ Very few requests remaining! Please add a GitHub token or wait for reset.")
                    elif remaining < 30:
                        st.warning("⚠️ Low on requests. Consider adding a GitHub token.")
                else:
                    st.error("Could not check rate limit status.")
            except Exception as e:
                st.error(f"Error checking rate limit: {str(e)}")

if __name__ == "__main__":
    main()
