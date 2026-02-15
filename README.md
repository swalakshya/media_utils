# Media Utils - PDF OCR Application

Convert your scanned PDFs into searchable PDFs using OCR (Optical Character Recognition). Supports multiple Indian languages including Hindi, Gujarati, Marathi, Tamil, and Telugu.

## 🚀 Quick Start for Windows Users (No Technical Knowledge Required!)

### Step 1: Install Docker Desktop

1. **Download Docker Desktop**
   - Visit: https://www.docker.com/products/docker-desktop/
   - Click the big blue "Download for Windows" button
   - Wait for the download to complete (about 500 MB)

2. **Install Docker Desktop**
   - Find the downloaded file (usually in your Downloads folder)
   - Double-click `Docker Desktop Installer.exe`
   - Click "OK" to allow the app to make changes
   - Wait for installation (takes 2-3 minutes)
   - Click "Close" when done
   - **Restart your computer** (important!)

3. **Start Docker Desktop**
   - After restart, Docker Desktop should start automatically
   - If not, find "Docker Desktop" in your Start menu and open it
   - Wait for Docker to fully start (you'll see a whale icon in your system tray at the bottom-right)
   - Accept the service agreement when prompted
   - You might see a tutorial - you can skip it

### Step 2: Find and Run Media Utils

1. **Open Docker Desktop**
   - Look for the whale icon in your system tray (bottom-right corner)
   - Click it, then click "Dashboard" OR
   - Find "Docker Desktop" in your Start menu

2. **Search for Media Utils**
   - At the top of Docker Desktop, you'll see a search bar
   - Type: `rajatjain/media-utils`
   - Press Enter or click the search icon
   - You'll see "rajatjain/media-utils" appear in the results

3. **Download (Pull) the Image**
   - Click on `rajatjain/media-utils`
   - Click the "Pull" button (it looks like a download icon)
   - Wait for it to download (2-3 GB, takes 5-10 minutes depending on your internet)
   - You'll see "Pull complete" when it's done

4. **Run the Container**
   - After pulling, click the ▶️ **Run** button next to the image
   - A popup will appear with "Optional Settings"
   - Click on "Optional Settings" to expand it
   - In the "Ports" section, you'll see a box labeled "Host Port"
   - Type `8000` in the Host Port box
   - Click the blue **Run** button at the bottom

5. **Container is Now Running!**
   - You'll see your container in the "Containers" tab
   - It will have a green status indicator

### Step 3: Use the Application

1. **Open Your Web Browser**
   - This is optimised for Chrome. So use browsers like Google Chrome, Microsoft Edge, Brave or Vivaldi

2. **Go to the Application**
   - In the address bar, type: `localhost:8000`
   - Press Enter
   - The Media Utils application will open!

3. **Process Your PDF**
   - Click "Select PDF File" and choose your scanned PDF
   - Select the language (Hindi, Gujarati, English, etc.)
   - Click "Process PDF"
   - Watch the progress bar with real-time updates
   - Your searchable PDF will download automatically when done!

## 🛑 How to Stop or Restart

### To Stop Media Utils

1. Open Docker Desktop
2. Go to the "Containers" tab (on the left side)
3. Find `media-utils` in the list
4. Click the ⏹️ **Stop** button (square icon)

### To Start It Again

1. Open Docker Desktop
2. Go to the "Containers" tab
3. Find `media-utils` in the list
4. Click the ▶️ **Start** button (play icon)
5. Wait 30 seconds, then go to `localhost:8000` in your browser

### To Remove It Completely

1. First, stop the container (see above)
2. Click the 🗑️ **Delete** button (trash icon) next to the container
3. Confirm deletion

## 🔄 Updating to the Latest Version

When a new version is available:

### Step 1: Stop the Running Container

1. Open Docker Desktop
2. Go to "Containers" tab
3. Find `media-utils` and click the ⏹️ **Stop** button

### Step 2: Remove the Old Container

1. Click the 🗑️ **Delete** button next to the stopped container
2. Confirm deletion

### Step 3: Pull the Latest Image

1. Go to "Images" tab in Docker Desktop (left sidebar)
2. Find `rajatjain/media-utils:latest` in the list
3. Click the ⋮ (three dots) menu next to it
4. Select **Pull** to download the latest version
5. Wait for the download to complete (you'll see "Pull complete")

### Step 4: Run the Updated Version

1. Click the ▶️ **Run** button next to the updated image
2. Click on "Optional Settings" to expand
3. Set Host Port to `8000`
4. Click the blue **Run** button
5. Wait 30 seconds, then access at `localhost:8000`

**That's it!** You're now running the latest version with all new features and fixes.

## ❓ Troubleshooting

### Problem: "Can't access localhost:8000"

**Solution 1**: Wait a bit longer
- After clicking "Run", wait 30-60 seconds
- The application needs time to start up
- Then try `localhost:8000` again

**Solution 2**: Check if it's running
- Open Docker Desktop
- Go to "Containers" tab
- Make sure `media-utils` has a green status
- If it's not green, click the ▶️ Start button

**Solution 3**: Restart everything
- In Docker Desktop, stop the container (⏹️ button)
- Wait 5 seconds
- Start it again (▶️ button)
- Wait 30 seconds
- Try `localhost:8000` in your browser

### Problem: "Port 8000 is already in use"

**What this means**: Another program is using port 8000

**Solution**: Use a different port
1. Stop and delete the existing container
2. Click "Run" again on the image
3. In "Optional Settings" → "Ports"
4. Instead of `8000`, type `8080` in the Host Port
5. Click Run
6. Access the app at `localhost:8080` instead

### Problem: Docker Desktop won't start

**Solution**:
1. Restart your computer
2. Make sure you have Windows 10/11 (64-bit)
3. Make sure virtualization is enabled in BIOS (usually enabled by default)
4. If still having issues, uninstall Docker Desktop and install it again

### Problem: Application is very slow

**Possible causes**:
- Your PDF has very high resolution images (this is good for quality!)
- Your computer needs more resources
- Large PDF file (100+ pages)

**What to do**:
- Be patient - OCR processing takes time
- The progress bar shows estimated time remaining
- You can process specific page ranges instead of the whole PDF

## 💡 Features

- ✅ **Multiple Languages**: Hindi, Gujarati, English, Marathi, Tamil, Telugu
- ✅ **Real-time Progress**: See exactly how long processing will take
- ✅ **Fast Processing**: Uses multiple CPU cores for speed
- ✅ **Easy to Use**: Simple web interface, just click and upload
- ✅ **Automatic Download**: Processed PDF downloads automatically
- ✅ **Cancel Anytime**: Stop processing if you need to
- ✅ **Page Range**: Process only specific pages if needed

## 🔒 Privacy & Security

- ✅ **100% Local Processing**: Everything happens on YOUR computer
- ✅ **No Internet Required**: After downloading Docker image, works offline
- ✅ **No Data Upload**: Your PDFs never leave your machine
- ✅ **No Cloud**: No third-party servers involved
- ✅ **Private**: Only you can access your files

## 📊 What to Expect

### Processing Speed
- **Small PDFs** (1-20 pages): 10-30 seconds
- **Medium PDFs** (20-100 pages): 1-5 minutes
- **Large PDFs** (100-500 pages): 5-15 minutes

### System Usage
- Uses 2-3 GB of RAM while running
- Uses 2 CPU cores for processing
- Better computer = faster processing

## ⚙️ System Requirements

**Minimum Requirements**:
- Windows 10/11 (64-bit)
- 4 GB RAM
- 5 GB free disk space
- Internet connection (only for initial download)

**Recommended**:
- Windows 11 (64-bit)
- 8 GB RAM or more
- 10 GB free disk space
- Multi-core processor

## 📝 Tips for Best Results

### For Better OCR Accuracy:
1. **Use high-quality scans**
   - Scan at 300 DPI or higher
   - Ensure text is clear, not blurry
   - Good lighting helps a lot

2. **Choose the right language**
   - Make sure you select the correct language
   - For mixed-language documents, choose the primary language

3. **Test with a few pages first**
   - Use the "Page Range" option
   - Process pages 1-5 to test quality
   - If good, process the full document

### For Faster Processing:
1. Close other programs to free up RAM
2. Process smaller PDFs or page ranges
3. Avoid running other heavy tasks simultaneously

## About This Project

This application helps make scanned PDFs searchable using state-of-the-art OCR technology. Perfect for:
- Digitizing old documents
- Making scanned books searchable
- Converting image-based PDFs to text-searchable PDFs
- Supporting Indian language documents

**No technical knowledge required. No subscription fees. Completely free and private.**

---
