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
            
            if display_
