# GitHub Pull Request Dashboard

A comprehensive Streamlit dashboard for analyzing GitHub pull requests. This application fetches PR data from any public GitHub repository and provides detailed analytics, visualizations, and data export capabilities.

## Features

- 📊 **Comprehensive PR Analysis**: View all PRs with detailed information including creation date, merge/close date, status, and time to completion
- 🔍 **Advanced Filtering**: Filter by status, authors, date ranges, and more
- 📈 **Rich Visualizations**: Interactive charts showing PR distributions, timelines, and contributor statistics
- 📥 **Data Export**: Download filtered data as CSV for further analysis
- 🔐 **GitHub API Integration**: Optional token support for higher rate limits and private repositories
- 🎨 **Interactive Interface**: User-friendly Streamlit interface with real-time updates

## Data Fields

The dashboard displays the following information for each pull request:

- **PR No**: Pull request number
- **PR Title**: Title of the pull request
- **Created Date**: When the PR was created
- **Merged Date**: When the PR was merged (if applicable)
- **Closed Date**: When the PR was closed (if applicable)
- **Status**: Current status (Open, Merged, Closed)
- **Link**: Direct link to the GitHub PR
- **Time to Merge/Close**: Number of days from creation to merge/close
- **Author**: PR creator
- **Labels**: Associated labels
- **Assignees**: Assigned reviewers
- **Comments**: Number of comments
- **Code Changes**: Additions, deletions, and changed files

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd PullRequestDashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Open your browser**
   The application will automatically open in your default browser at `http://localhost:8501`

## Usage

### Basic Usage

1. **Enter Repository Information**
   - In the sidebar, enter a GitHub repository URL or owner/repo format
   - Examples:
     - `microsoft/vscode`
     - `https://github.com/facebook/react`
     - `tensorflow/tensorflow`

2. **Optional: Add GitHub Token**
   - For higher rate limits (5000 requests/hour vs 60)
   - Required for private repositories
   - Create a token at: https://github.com/settings/tokens

3. **Fetch Data**
   - Click "Fetch PR Data" button
   - Wait for the data to load (may take a few moments for large repositories)

4. **Analyze Results**
   - View summary metrics at the top
   - Use filters to refine your analysis
   - Explore interactive visualizations
   - Download data as CSV for further analysis

### Advanced Features

#### Filtering Options
- **Status Filter**: Show only Open, Merged, or Closed PRs
- **Author Filter**: Focus on specific contributors
- **Date Range**: Analyze PRs within a specific time period

#### Visualizations
- **Status Distribution**: Pie chart showing PR status breakdown
- **Time to Close**: Histogram of days taken to merge/close PRs
- **Timeline**: Line chart showing PR creation over time
- **Top Contributors**: Bar chart of most active contributors

#### Data Export
- Click "📥 Download CSV" to export filtered data
- File includes all available fields for further analysis
- Filename format: `{owner}_{repo}_pr_data.csv`

## GitHub API Rate Limits

⚠️ **Important**: The GitHub API has strict rate limits that you need to be aware of:

- **Without Token**: 60 requests per hour (very limited)
- **With Token**: 5,000 requests per hour (recommended)
- **Large Repositories**: Will definitely require a token to fetch all data

### Getting a GitHub Personal Access Token (Recommended)

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "PR Dashboard")
4. Select expiration (30 days recommended for testing)
5. **No scopes needed** for public repositories (leave all checkboxes unchecked)
6. Click "Generate token"
7. Copy the token and paste it in the sidebar of the app

**Note**: The token is only stored in your browser session and is not saved anywhere.

## Example Repositories to Try

- `microsoft/vscode` - Popular code editor
- `facebook/react` - React JavaScript library
- `tensorflow/tensorflow` - Machine learning framework
- `kubernetes/kubernetes` - Container orchestration
- `nodejs/node` - Node.js runtime
- `python/cpython` - Python programming language

## Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**
   - Add a GitHub personal access token
   - Wait for the rate limit to reset (1 hour)

2. **Repository Not Found**
   - Check the repository name spelling
   - Ensure the repository is public (or provide a token for private repos)

3. **No Data Displayed**
   - Repository might not have any pull requests
   - Check if the repository exists and is accessible

4. **Slow Loading**
   - Large repositories may take time to fetch all data
   - The app limits to 1000 PRs to prevent excessive API calls

### Error Messages

- **403 Forbidden**: Rate limit exceeded or private repository without token
- **404 Not Found**: Repository doesn't exist or is private
- **422 Unprocessable Entity**: Invalid repository format

## Technical Details

### Architecture
- **Frontend**: Streamlit web framework
- **Data Processing**: Pandas for data manipulation
- **Visualizations**: Plotly for interactive charts
- **API Integration**: GitHub REST API v3

### Performance Considerations
- **Simple & Efficient**: Always fetches only the last 100 PRs (most recent) from any repository
- **Single API Call**: Uses only 1 API request per repository analysis
- **Rate Limit Friendly**: Minimizes API usage to work reliably even without tokens
- Data is cached in session state for filtering operations
- Fast loading and responsive interface

### Security
- GitHub tokens are handled securely (password input type)
- No data is stored permanently on the server
- All API calls use HTTPS

## Contributing

Feel free to contribute to this project by:
- Reporting bugs
- Suggesting new features
- Submitting pull requests
- Improving documentation

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Review GitHub API documentation
3. Create an issue in the repository

---

**Happy analyzing! 🚀**
