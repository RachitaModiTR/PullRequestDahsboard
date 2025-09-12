# GitHub Repository Setup Instructions

## Step 1: Create a New Repository on GitHub

1. Go to [GitHub.com](https://github.com) and sign in to your account
2. Click the "+" icon in the top right corner and select "New repository"
3. Fill in the repository details:
   - **Repository name**: `pull-request-dashboard` (or your preferred name)
   - **Description**: `Streamlit dashboard for analyzing GitHub pull requests`
   - **Visibility**: Choose Public or Private based on your preference
   - **DO NOT** initialize with README, .gitignore, or license (since we already have these files)
4. Click "Create repository"

## Step 2: Push Your Local Repository to GitHub

After creating the repository, GitHub will show you the commands to run. Use the "push an existing repository from the command line" section:

```bash
# Add the GitHub repository as remote origin
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git

# Push your code to GitHub
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPOSITORY_NAME` with your actual GitHub username and the repository name you chose.

## Step 3: Verify Upload

1. Refresh your GitHub repository page
2. You should see all your files:
   - `app.py` (main dashboard application)
   - `requirements.txt` (Python dependencies)
   - `README.md` (documentation)
   - `.gitignore` (Git ignore rules)

## Step 4: Share Your Repository

Once uploaded, you can share your repository by:
- Sending the repository URL: `https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME`
- Others can clone it using: `git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git`

## Troubleshooting

If you encounter authentication issues:
1. Use a Personal Access Token instead of password
2. Generate one at: Settings → Developer settings → Personal access tokens → Tokens (classic)
3. Select scopes: `repo` (for private repos) or `public_repo` (for public repos)
4. Use the token as your password when prompted

## Next Steps for Collaborators

Anyone who clones your repository can run the dashboard by:
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
cd YOUR_REPOSITORY_NAME
pip install -r requirements.txt
streamlit run app.py
