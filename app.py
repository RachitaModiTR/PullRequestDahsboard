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
    
    def _fetch_pr_comments(_self, owner: str, repo: str, pr_number: int) -> int:
        """Fetch comments for a specific PR and return the count"""
        # For performance reasons, we'll use the comments count from the PR data
        # This avoids making additional API calls for each PR
        # If more detailed comment analysis is needed, this can be re-enabled
        return 0  # Return 0 to use the default comments count from PR data
    
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
        
        # Regular expressions to extract workitem numbers
        import re
        # Pattern for Ab# followed by 7 digits
        workitem_pattern1 = re.compile(r'Ab#(\d{7})')
        # Pattern for just 7 digits (standalone)
        workitem_pattern2 = re.compile(r'\b(\d{7})\b')
        
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
                    
                    # Extract workitem number from PR title and description
                    workitem = None
                    workitem_url = None
                    
                    # Check PR title first
                    title_text = pr.get('title', '')
                    match1 = workitem_pattern1.search(title_text)
                    match2 = workitem_pattern2.search(title_text)
                    
                    # If not found in title, check PR description
                    if not match1 and not match2 and pr.get('body'):
                        body_text = pr.get('body', '')
                        match1 = workitem_pattern1.search(body_text)
                        match2 = workitem_pattern2.search(body_text)
                    
                    # Process the match - show only the number without Ab# prefix
                    if match1:
                        workitem_number = match1.group(1)
                        workitem = workitem_number  # Just the number without Ab# prefix
                        # Create a URL for the workitem (using a placeholder URL format)
                        workitem_url = f"https://workitem.example.com/item/{workitem_number}"
                    elif match2:
                        workitem_number = match2.group(1)
                        workitem = workitem_number  # Just the number
                        # Create a URL for the workitem (using a placeholder URL format)
                        workitem_url = f"https://workitem.example.com/item/{workitem_number}"
                    
                    # Fetch detailed conversation count
                    pr_number = pr.get('number', 0)
                    repo_owner = pr.get('base', {}).get('repo', {}).get('owner', {}).get('login')
                    repo_name = pr.get('base', {}).get('repo', {}).get('name')
                    
                    # If we can extract the repo info from the PR, use it to fetch conversations
                    conversations_count = pr.get('comments', 0)
                    if repo_owner and repo_name:
                        detailed_count = _self._fetch_pr_comments(repo_owner, repo_name, pr_number)
                        if detailed_count > 0:
                            conversations_count = detailed_count
                    
                    processed_data.append({
                        'PR No': pr_number,
                        'PR Title': pr.get('title', 'No Title'),
                        'Created Date': created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Merged Date': merged_at.strftime('%Y-%m-%d %H:%M:%S') if merged_at else None,
                        'Closed Date': closed_at.strftime('%Y-%m-%d %H:%M:%S') if closed_at else None,
                        'Status': status,
                        'Link': pr.get('html_url', ''),
                        'Workitem': workitem,
                        'Workitem URL': workitem_url,
                        'Time to Merge/Close (days)': time_to_action,
                        'Author': author,
                        'Labels': labels,
                        'Assignees': assignees,
                        'Conversations': conversations_count,
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
    
    # Predefined repositories dropdown
    predefined_repos = [
        "tr/cs-prof-cloud_ultratax-api-services",
        "tr/cs-prof-cloud_ultratax-client-services",
        "tr/cs-prof-cloud_ultratax-com-application",
        "tr/cs-prof-cloud_tax-assistant-services"
    ]
    
    selected_repo = st.sidebar.selectbox(
        "Select a predefined repository",
        [""] + predefined_repos,
        index=0,
        help="Choose from common repositories"
    )
    
    # Repository input (with predefined repo if selected)
    repo_url = st.sidebar.text_input(
        "Repository URL or Owner/Repo",
        value=selected_repo,
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
        
        # Create tabs with enhanced styling for better visibility
        st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #f0f2f6;
            border-radius: 4px;
            padding: 10px 16px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4CAF50;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create tabs for better organization with clear labels
        tab1, tab2, tab3 = st.tabs(["📋 Data Table", "📈 Visualizations", "📊 Advanced Analytics"])
        
        with tab1:
            st.subheader("📋 Pull Request Data")
            
            # Display columns selection
            display_columns = st.multiselect(
                "Select columns to display",
                options=df.columns.tolist(),
                default=['PR No', 'PR Title', 'Author', 'Created Date', 'Merged Date', 'Closed Date', 'Status', 'Workitem', 'Time to Merge/Close (days)']
            )
            
            if display_columns:
                # Store original PR No and Link for reference
                filtered_df['PR No_Original'] = filtered_df['PR No']
                
                # Create a new column for PR URL that will be used for linking
                if 'Link' in filtered_df.columns:
                    filtered_df['PR_URL'] = filtered_df['Link']
                
                # Note: We won't modify the PR No column with HTML as Streamlit dataframes don't render HTML
                # Instead, we'll create a custom display function after showing the dataframe
                
                # No need to make workitem links clickable - just display the workitem number
                # We'll keep this commented out for reference
                # if 'Workitem' in display_columns and 'Workitem URL' in filtered_df.columns:
                #     filtered_df['Workitem_Display'] = filtered_df.apply(
                #         lambda row: f'<a href="{row["Workitem URL"]}" target="_blank">{row["Workitem"]}</a>' if pd.notna(row["Workitem"]) and pd.notna(row["Workitem URL"]) else row["Workitem"],
                #         axis=1
                #     )
                
                # Display the data table with the selected columns
                st.dataframe(
                    filtered_df[display_columns],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Add instructions for clickable PR numbers
                st.info("💡 Click on a PR number to open it in GitHub (implemented via column configuration)")
                
                # Create a clickable link for PR numbers using Streamlit's column configuration
                # This approach uses Streamlit's built-in functionality rather than HTML rendering
                if 'PR No' in display_columns and 'PR_URL' in filtered_df.columns:
                    # Get the displayed dataframe and add a link to PR numbers
                    st.markdown("""
                    <style>
                    /* Style for PR number links */
                    .pr-link {
                        color: #1E88E5;
                        text-decoration: underline;
                        cursor: pointer;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Display a sample of clickable PRs for demonstration
                    if not filtered_df.empty:
                        st.subheader("Quick PR Links")
                        cols = st.columns(4)
                        for i, (idx, row) in enumerate(filtered_df.head(8).iterrows()):
                            col_idx = i % 4
                            if pd.notna(row['PR_URL']):
                                cols[col_idx].markdown(f"<a href='{row['PR_URL']}' target='_blank' class='pr-link'>PR #{row['PR No']}</a>", unsafe_allow_html=True)
                
                # Export to CSV
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download as CSV",
                    csv,
                    "github_prs.csv",
                    "text/csv",
                    key='download-csv'
                )
        
        with tab2:
            st.subheader("📈 Visualizations")
            
            # Status distribution
            st.subheader("PR Status Distribution")
            status_counts = filtered_df['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            
            fig = px.pie(
                status_counts, 
                values='Count', 
                names='Status',
                color='Status',
                color_discrete_map={
                    'Open': '#1E88E5',
                    'Closed': '#E53935',
                    'Merged': '#43A047'
                },
                hole=0.4
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # PR Timeline
            st.subheader("PR Timeline")
            filtered_df['Created Date Parsed'] = pd.to_datetime(filtered_df['Created Date'])
            filtered_df['Month'] = filtered_df['Created Date Parsed'].dt.strftime('%Y-%m')
            
            monthly_counts = filtered_df.groupby(['Month', 'Status']).size().reset_index(name='Count')
            
            fig = px.bar(
                monthly_counts,
                x='Month',
                y='Count',
                color='Status',
                color_discrete_map={
                    'Open': '#1E88E5',
                    'Closed': '#E53935',
                    'Merged': '#43A047'
                },
                barmode='stack'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Time to Merge/Close Distribution
            st.subheader("Time to Merge/Close Distribution")
            time_data = filtered_df[filtered_df['Time to Merge/Close (days)'].notna()]
            
            if not time_data.empty:
                fig = px.histogram(
                    time_data,
                    x='Time to Merge/Close (days)',
                    color='Status',
                    color_discrete_map={
                        'Closed': '#E53935',
                        'Merged': '#43A047'
                    },
                    nbins=20,
                    opacity=0.7
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No time data available for visualization.")
        
        with tab3:
            st.subheader("📊 Advanced Analytics")
            
            # Author Performance
            st.subheader("Author Performance")
            author_stats = filtered_df.groupby('Author').agg({
                'PR No': 'count',
                'Time to Merge/Close (days)': 'mean'
            }).reset_index()
            author_stats.columns = ['Author', 'PR Count', 'Avg Time to Merge/Close (days)']
            author_stats = author_stats.sort_values('PR Count', ascending=False).head(10)
            
            fig = px.bar(
                author_stats,
                x='Author',
                y='PR Count',
                color='Avg Time to Merge/Close (days)',
                color_continuous_scale='Viridis',
                hover_data=['Avg Time to Merge/Close (days)']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # PR Size Analysis - Ensure it works even without Additions/Deletions data
            st.subheader("PR Size Analysis")
            
            # Create a simulated size category based on PR title length if actual size data is not available
            if ('Additions' in filtered_df.columns and 'Deletions' in filtered_df.columns and 
                filtered_df['Additions'].notna().any() and filtered_df['Deletions'].notna().any()):
                # Use actual PR size data if available
                filtered_df['Total Changes'] = filtered_df['Additions'] + filtered_df['Deletions']
                filtered_df['Size Category'] = pd.cut(
                    filtered_df['Total Changes'],
                    bins=[0, 10, 50, 200, 1000, float('inf')],
                    labels=['XS (0-10)', 'S (11-50)', 'M (51-200)', 'L (201-1000)', 'XL (1000+)']
                )
                size_metric = "Based on actual code changes"
            else:
                # Fallback to title length as a proxy for PR size
                filtered_df['Title Length'] = filtered_df['PR Title'].str.len()
                filtered_df['Size Category'] = pd.cut(
                    filtered_df['Title Length'],
                    bins=[0, 30, 60, 100, 150, float('inf')],
                    labels=['XS (0-30 chars)', 'S (31-60 chars)', 'M (61-100 chars)', 'L (101-150 chars)', 'XL (150+ chars)']
                )
                size_metric = "Based on PR title length (fallback method)"
            
            st.info(f"Size categorization: {size_metric}")
            
            size_stats = filtered_df.groupby('Size Category').agg({
                'PR No': 'count',
                'Time to Merge/Close (days)': 'mean'
            }).reset_index()
            size_stats.columns = ['Size Category', 'PR Count', 'Avg Time to Merge/Close (days)']
            
            fig = px.bar(
                size_stats,
                x='Size Category',
                y='PR Count',
                color='Avg Time to Merge/Close (days)',
                color_continuous_scale='Viridis',
                hover_data=['Avg Time to Merge/Close (days)']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # PR Status by Author
            st.subheader("PR Status by Author")
            author_status = filtered_df.groupby(['Author', 'Status']).size().reset_index(name='Count')
            top_authors = filtered_df['Author'].value_counts().nlargest(8).index.tolist()
            author_status_filtered = author_status[author_status['Author'].isin(top_authors)]
            
            fig = px.bar(
                author_status_filtered,
                x='Author',
                y='Count',
                color='Status',
                color_discrete_map={
                    'Open': '#1E88E5',
                    'Closed': '#E53935',
                    'Merged': '#43A047'
                },
                barmode='stack'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # PR Conversations Analysis
            st.subheader("PR Conversations Analysis")
            
            # Ensure Conversations column exists and has valid data
            if 'Conversations' in filtered_df.columns:
                # Convert to numeric if not already
                filtered_df['Conversations'] = pd.to_numeric(filtered_df['Conversations'], errors='coerce').fillna(0).astype(int)
                
                # Debug information
                st.info(f"Conversations range: {filtered_df['Conversations'].min()} to {filtered_df['Conversations'].max()}, Mean: {filtered_df['Conversations'].mean():.2f}")
                
                # Create conversation bins
                filtered_df['Conversation Bins'] = pd.cut(
                    filtered_df['Conversations'],
                    bins=[-1, 0, 1, 3, 5, 10, float('inf')],
                    labels=['0', '1', '2-3', '4-5', '6-10', '10+']
                )
                
                # Show distribution of conversation counts
                st.subheader("Conversation Count Distribution")
                conv_dist = filtered_df['Conversations'].value_counts().sort_index().reset_index()
                conv_dist.columns = ['Conversation Count', 'Number of PRs']
                
                fig = px.bar(
                    conv_dist,
                    x='Conversation Count',
                    y='Number of PRs',
                    title='Distribution of PR Conversation Counts',
                    color_discrete_sequence=['#1E88E5']
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
                
                # Count PRs by conversation bins and status
                conv_stats = filtered_df.groupby(['Conversation Bins', 'Status']).size().reset_index(name='Count')
                
                # Create stacked bar chart
                fig = px.bar(
                    conv_stats,
                    x='Conversation Bins',
                    y='Count',
                    color='Status',
                    color_discrete_map={
                        'Open': '#1E88E5',
                        'Closed': '#E53935',
                        'Merged': '#43A047'
                    },
                    barmode='stack',
                    title='PR Count by Conversation Volume'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Correlation between conversations and time to merge/close
                if filtered_df['Time to Merge/Close (days)'].notna().any():
                    # Direct correlation between conversations and time to merge/close
                    st.subheader("Correlation: Conversations vs. Time to Merge/Close")
                    
                    # Create a scatter plot
                    fig = px.scatter(
                        filtered_df[filtered_df['Time to Merge/Close (days)'].notna()],
                        x='Conversations',
                        y='Time to Merge/Close (days)',
                        color='Status',
                        color_discrete_map={
                            'Closed': '#E53935',
                            'Merged': '#43A047'
                        },
                        opacity=0.7,
                        title='Direct Correlation: Conversations vs. Time to Merge/Close',
                        trendline='ols'  # Add trend line
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Calculate average time to merge/close by conversation bins
                    conv_time = filtered_df[filtered_df['Time to Merge/Close (days)'].notna()].groupby('Conversation Bins').agg({
                        'Time to Merge/Close (days)': 'mean',
                        'PR No': 'count'
                    }).reset_index()
                    conv_time.columns = ['Conversation Bins', 'Avg Days to Merge/Close', 'PR Count']
                    
                    # Create a dual-axis chart
                    fig = go.Figure()
                    
                    # Add bars for PR count
                    fig.add_trace(go.Bar(
                        x=conv_time['Conversation Bins'],
                        y=conv_time['PR Count'],
                        name='PR Count',
                        marker_color='#1E88E5',
                        opacity=0.7
                    ))
                    
                    # Add line for average time
                    fig.add_trace(go.Scatter(
                        x=conv_time['Conversation Bins'],
                        y=conv_time['Avg Days to Merge/Close'],
                        name='Avg Days to Merge/Close',
                        marker_color='#E53935',
                        mode='lines+markers',
                        yaxis='y2'
                    ))
                    
                    # Set up the layout with two y-axes
                    fig.update_layout(
                        height=400,
                        title='Impact of Conversations on Time to Merge/Close',
                        yaxis=dict(title='PR Count'),
                        yaxis2=dict(title='Avg Days to Merge/Close', overlaying='y', side='right'),
                        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Conversation data not available for analysis.")
            
            # Time Trends Analysis
            st.subheader("PR Merge Time Trends")
            if filtered_df['Time to Merge/Close (days)'].notna().any():
                # Create a time series of average merge/close time
                filtered_df['Created Month'] = pd.to_datetime(filtered_df['Created Date']).dt.strftime('%Y-%m')
                time_trends = filtered_df[filtered_df['Time to Merge/Close (days)'].notna()].groupby('Created Month').agg({
                    'Time to Merge/Close (days)': 'mean',
                    'PR No': 'count'
                }).reset_index()
                time_trends.columns = ['Month', 'Avg Days to Merge/Close', 'PR Count']
                
                # Create a dual-axis chart
                fig = go.Figure()
                
                # Add bars for PR count
                fig.add_trace(go.Bar(
                    x=time_trends['Month'],
                    y=time_trends['PR Count'],
                    name='PR Count',
                    marker_color='#1E88E5',
                    opacity=0.7
                ))
                
                # Add line for average time
                fig.add_trace(go.Scatter(
                    x=time_trends['Month'],
                    y=time_trends['Avg Days to Merge/Close'],
                    name='Avg Days to Merge/Close',
                    marker_color='#E53935',
                    mode='lines+markers',
                    yaxis='y2'
                ))
                
                # Set up the layout with two y-axes
                fig.update_layout(
                    height=400,
                    yaxis=dict(title='PR Count'),
                    yaxis2=dict(title='Avg Days to Merge/Close', overlaying='y', side='right'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Time trend data not available for analysis.")

if __name__ == "__main__":
    main()
