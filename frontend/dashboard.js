// DHI Transaction Analytics Dashboard JavaScript
class DashboardApp {
    constructor() {
        this.config = {
            plaidApiUrl: 'http://localhost:8080',
            neo4jUrl: 'bolt://localhost:7687',
            refreshInterval: 30000 // 30 seconds
        };
        
        this.charts = {};
        this.mediaRecorder = null;
        this.currentStream = null;
        this.recordedChunks = [];
        this.recordings = [];
        this.uploads = [];
        this.capturedPhotos = [];
        this.currentCamera = 'user'; // 'user' for front, 'environment' for back
        
        // New properties for LLM and database features
        this.llmQueryHistory = [];
        this.databaseConnections = [];
        this.queryCounter = 0;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSettings();
        this.checkApiStatus();
        this.loadDashboard();
        this.startAutoRefresh();
        this.initializeToasts();
        this.loadDatabaseConnections();
    }

    setupEventListeners() {
        // Sidebar navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                this.navigateToSection(e.target.dataset.section);
            });
        });

        // Mobile sidebar toggle
        document.getElementById('toggleSidebar').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('show');
        });

        // Camera controls
        document.getElementById('startCamera').addEventListener('click', () => this.startCamera());
        document.getElementById('capturePhoto').addEventListener('click', () => this.capturePhoto());
        document.getElementById('stopCamera').addEventListener('click', () => this.stopCamera());
        document.getElementById('switchCamera').addEventListener('click', () => this.switchCamera());

        // Audio recording controls
        document.getElementById('recordButton').addEventListener('click', () => this.toggleRecording());

        // File upload
        this.setupFileUpload();

        // New LLM and database event listeners
        this.setupLLMEventListeners();
        this.setupDatabaseEventListeners();
    }

    setupLLMEventListeners() {
        // LLM query execution
        document.getElementById('executeLLMQuery').addEventListener('click', () => this.executeLLMQuery());
        
        // Query examples
        document.querySelectorAll('.query-example').forEach(button => {
            button.addEventListener('click', (e) => {
                document.getElementById('llmQueryInput').value = e.target.dataset.query;
            });
        });
        
        // Enter key to execute query
        document.getElementById('llmQueryInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.executeLLMQuery();
            }
        });
    }

    setupDatabaseEventListeners() {
        // Database connection management
        document.getElementById('saveDatabaseConnection').addEventListener('click', () => this.saveDatabaseConnection());
        document.getElementById('testDatabaseConnection').addEventListener('click', () => this.testDatabaseConnection());
        
        // Direct query execution
        document.getElementById('executeDirectQuery').addEventListener('click', () => this.executeDirectQuery());
        
        // Database type auto-fill ports
        document.getElementById('dbType').addEventListener('change', (e) => {
            const portInput = document.getElementById('dbPort');
            const portMap = {
                'postgresql': 5432,
                'mysql': 3306,
                'sqlite': 0,
                'neo4j': 7687,
                'redis': 6379,
                'mongodb': 27017
            };
            
            if (portMap[e.target.value]) {
                portInput.value = portMap[e.target.value];
            }
        });
    }

    navigateToSection(section) {
        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-section="${section}"]`).classList.add('active');

        // Hide all sections
        document.querySelectorAll('.content-section').forEach(sec => {
            sec.style.display = 'none';
        });

        // Show selected section
        document.getElementById(`${section}-section`).style.display = 'block';

        // Update page title
        const titles = {
            dashboard: 'Dashboard',
            analytics: 'Analytics',
            status: 'API Status',
            media: 'Media Capture',
            upload: 'File Upload',
            audio: 'Audio Recording',
            transactions: 'Transactions',
            settings: 'Settings'
        };
        document.getElementById('pageTitle').textContent = titles[section];

        // Load section-specific data
        this.loadSectionData(section);

        // Hide sidebar on mobile
        if (window.innerWidth <= 768) {
            document.getElementById('sidebar').classList.remove('show');
        }
    }

    loadSectionData(section) {
        switch (section) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
            case 'status':
                this.loadApiStatus();
                break;
            case 'transactions':
                this.loadTransactions();
                break;
        }
    }

    async checkApiStatus() {
        const connectionStatus = document.getElementById('connectionStatus');
        const plaidApiStatus = document.getElementById('plaidApiStatus');
        const neo4jStatus = document.getElementById('neo4jStatus');

        try {
            // Check Plaid API
            const plaidResponse = await fetch(`${this.config.plaidApiUrl}/health`);
            if (plaidResponse.ok) {
                this.updateStatusIndicator(connectionStatus, 'online', 'Connected');
                if (plaidApiStatus) this.updateStatusIndicator(plaidApiStatus, 'online', 'Online');
            } else {
                throw new Error('Plaid API not responding');
            }
        } catch (error) {
            this.updateStatusIndicator(connectionStatus, 'offline', 'Offline');
            if (plaidApiStatus) this.updateStatusIndicator(plaidApiStatus, 'offline', 'Offline');
        }

        // Note: Neo4j status would need a backend endpoint to check
        if (neo4jStatus) {
            this.updateStatusIndicator(neo4jStatus, 'loading', 'Unknown');
        }
    }

    updateStatusIndicator(element, status, text) {
        element.className = `status-indicator status-${status}`;
        element.innerHTML = `<i class="fas fa-circle me-1"></i>${text}`;
    }

    async loadDashboard() {
        try {
            // Load dashboard statistics
            const [accountsRes, transactionsRes] = await Promise.all([
                fetch(`${this.config.plaidApiUrl}/accounts`),
                fetch(`${this.config.plaidApiUrl}/transactions`)
            ]);

            const accountsData = await accountsRes.json();
            const transactionsData = await transactionsRes.json();

            this.updateDashboardStats(accountsData.data, transactionsData.data);
            this.createCharts(transactionsData.data);
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showToast('Error loading dashboard data', 'error');
        }
    }

    updateDashboardStats(accounts, transactions) {
        document.getElementById('totalTransactions').textContent = transactions.length;
        document.getElementById('totalAmount').textContent = `$${transactions.reduce((sum, t) => sum + parseFloat(t.amount), 0).toFixed(2)}`;
        
        const uniqueMerchants = new Set(transactions.map(t => t.merchant_name).filter(Boolean));
        document.getElementById('totalMerchants').textContent = uniqueMerchants.size;
        
        // Simple anomaly detection (transactions > 2x average)
        const amounts = transactions.map(t => parseFloat(t.amount));
        const avgAmount = amounts.reduce((a, b) => a + b, 0) / amounts.length;
        const anomalies = amounts.filter(amount => amount > avgAmount * 2);
        document.getElementById('anomalies').textContent = anomalies.length;
    }

    createCharts(transactions) {
        this.createCategoryChart(transactions);
        this.createTrendChart(transactions);
    }

    createCategoryChart(transactions) {
        const ctx = document.getElementById('categoryChart').getContext('2d');
        
        // Group by category
        const categoryData = {};
        transactions.forEach(t => {
            const category = t.category || 'Other';
            categoryData[category] = (categoryData[category] || 0) + parseFloat(t.amount);
        });

        const labels = Object.keys(categoryData);
        const data = Object.values(categoryData);
        const colors = [
            '#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6b7280'
        ];

        if (this.charts.category) {
            this.charts.category.destroy();
        }

        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    createTrendChart(transactions) {
        const ctx = document.getElementById('trendChart').getContext('2d');
        
        // Group by month
        const monthlyData = {};
        transactions.forEach(t => {
            const month = t.date.substring(0, 7); // YYYY-MM
            monthlyData[month] = (monthlyData[month] || 0) + parseFloat(t.amount);
        });

        const labels = Object.keys(monthlyData).sort();
        const data = labels.map(label => monthlyData[label]);

        if (this.charts.trend) {
            this.charts.trend.destroy();
        }

        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monthly Spending',
                    data: data,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });
    }

    async loadAnalytics() {
        try {
            const response = await fetch(`${this.config.plaidApiUrl}/transactions`);
            const data = await response.json();
            this.showAnalytics('spending', data.data);
        } catch (error) {
            console.error('Error loading analytics:', error);
            this.showToast('Error loading analytics data', 'error');
        }
    }

    showAnalytics(type, data = null) {
        // Update active button
        document.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');

        if (!data) {
            // Load data if not provided
            this.loadAnalytics();
            return;
        }

        const ctx = document.getElementById('analyticsChart').getContext('2d');
        
        if (this.charts.analytics) {
            this.charts.analytics.destroy();
        }

        switch (type) {
            case 'spending':
                this.createSpendingAnalytics(ctx, data);
                break;
            case 'merchants':
                this.createMerchantAnalytics(ctx, data);
                break;
            case 'anomalies':
                this.createAnomalyAnalytics(ctx, data);
                break;
        }
    }

    createSpendingAnalytics(ctx, transactions) {
        const dailyData = {};
        transactions.forEach(t => {
            const date = t.date;
            dailyData[date] = (dailyData[date] || 0) + parseFloat(t.amount);
        });

        const labels = Object.keys(dailyData).sort();
        const data = labels.map(label => dailyData[label]);

        this.charts.analytics = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Spending',
                    data: data,
                    backgroundColor: '#2563eb',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });
    }

    createMerchantAnalytics(ctx, transactions) {
        const merchantData = {};
        transactions.forEach(t => {
            const merchant = t.merchant_name || 'Unknown';
            merchantData[merchant] = (merchantData[merchant] || 0) + parseFloat(t.amount);
        });

        const sortedMerchants = Object.entries(merchantData)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10);

        const labels = sortedMerchants.map(([merchant]) => merchant);
        const data = sortedMerchants.map(([, amount]) => amount);

        this.charts.analytics = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Spending by Merchant',
                    data: data,
                    backgroundColor: '#10b981'
                }]
            },
            options: {
                responsive: true,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });
    }

    createAnomalyAnalytics(ctx, transactions) {
        const amounts = transactions.map(t => parseFloat(t.amount));
        const avgAmount = amounts.reduce((a, b) => a + b, 0) / amounts.length;
        const stdDev = Math.sqrt(amounts.reduce((sq, n) => sq + Math.pow(n - avgAmount, 2), 0) / amounts.length);
        
        const anomalies = transactions.filter(t => {
            const amount = parseFloat(t.amount);
            return Math.abs(amount - avgAmount) > 2 * stdDev;
        });

        const labels = anomalies.map(t => t.date);
        const data = anomalies.map(t => parseFloat(t.amount));

        this.charts.analytics = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Anomalous Transactions',
                    data: data.map((amount, i) => ({x: i, y: amount})),
                    backgroundColor: '#ef4444',
                    borderColor: '#dc2626',
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });
    }

    loadApiStatus() {
        this.checkApiStatus();
        this.loadSystemLogs();
    }

    loadSystemLogs() {
        const logsContainer = document.getElementById('systemLogs');
        const logs = [
            `[${new Date().toISOString()}] System started successfully`,
            `[${new Date().toISOString()}] Checking API endpoints...`,
            `[${new Date().toISOString()}] Plaid API: ${this.config.plaidApiUrl}`,
            `[${new Date().toISOString()}] Neo4j: ${this.config.neo4jUrl}`,
            `[${new Date().toISOString()}] Dashboard ready`
        ];
        
        logsContainer.innerHTML = logs.join('<br>');
    }

    async loadTransactions() {
        try {
            const response = await fetch(`${this.config.plaidApiUrl}/transactions`);
            const data = await response.json();
            this.renderTransactionsTable(data.data);
        } catch (error) {
            console.error('Error loading transactions:', error);
            this.showToast('Error loading transactions', 'error');
        }
    }

    renderTransactionsTable(transactions) {
        const tbody = document.getElementById('transactionsTableBody');
        
        if (transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No transactions found</td></tr>';
            return;
        }

        tbody.innerHTML = transactions.slice(0, 50).map(t => `
            <tr>
                <td>${t.date}</td>
                <td>${t.name}</td>
                <td>$${parseFloat(t.amount).toFixed(2)}</td>
                <td><span class="badge bg-primary">${t.category || 'Other'}</span></td>
                <td>${t.merchant_name || 'Unknown'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="dashboard.viewTransactionDetails('${t.transaction_id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    // Camera functionality
    async startCamera() {
        try {
            const constraints = {
                video: {
                    facingMode: this.currentCamera,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };

            this.currentStream = await navigator.mediaDevices.getUserMedia(constraints);
            const video = document.getElementById('videoElement');
            video.srcObject = this.currentStream;

            document.getElementById('startCamera').style.display = 'none';
            document.getElementById('capturePhoto').style.display = 'inline-block';
            document.getElementById('stopCamera').style.display = 'inline-block';
            document.getElementById('switchCamera').style.display = 'inline-block';

            this.showToast('Camera started successfully', 'success');
        } catch (error) {
            console.error('Error starting camera:', error);
            this.showToast('Error starting camera: ' + error.message, 'error');
        }
    }

    capturePhoto() {
        const video = document.getElementById('videoElement');
        const canvas = document.getElementById('captureCanvas');
        const ctx = canvas.getContext('2d');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);

        canvas.toBlob(blob => {
            const url = URL.createObjectURL(blob);
            const photo = {
                id: Date.now(),
                url: url,
                timestamp: new Date().toISOString(),
                blob: blob
            };

            this.capturedPhotos.push(photo);
            this.updateCapturedPhotos();
            this.showToast('Photo captured successfully', 'success');
        }, 'image/jpeg');
    }

    stopCamera() {
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
            this.currentStream = null;
        }

        document.getElementById('startCamera').style.display = 'inline-block';
        document.getElementById('capturePhoto').style.display = 'none';
        document.getElementById('stopCamera').style.display = 'none';
        document.getElementById('switchCamera').style.display = 'none';

        this.showToast('Camera stopped', 'info');
    }

    switchCamera() {
        this.currentCamera = this.currentCamera === 'user' ? 'environment' : 'user';
        this.stopCamera();
        setTimeout(() => this.startCamera(), 500);
    }

    updateCapturedPhotos() {
        const container = document.getElementById('capturedPhotos');
        
        if (this.capturedPhotos.length === 0) {
            container.innerHTML = '<div class="col-12 text-center text-muted">No photos captured yet</div>';
            return;
        }

        container.innerHTML = this.capturedPhotos.map(photo => `
            <div class="col-6 mb-2">
                <img src="${photo.url}" class="img-fluid rounded" alt="Captured photo">
                <div class="text-center mt-1">
                    <small class="text-muted">${new Date(photo.timestamp).toLocaleTimeString()}</small>
                </div>
            </div>
        `).join('');
    }

    // Audio recording functionality
    async toggleRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.recordedChunks = [];

            this.mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.recordedChunks, { type: 'audio/webm' });
                const url = URL.createObjectURL(blob);
                
                document.getElementById('audioPlayback').src = url;
                document.getElementById('audioPlayback').style.display = 'block';
                document.getElementById('audioControls').style.display = 'flex';
                
                // Store the recording
                this.currentRecording = { blob, url, timestamp: new Date().toISOString() };
            };

            this.mediaRecorder.start();
            
            const recordButton = document.getElementById('recordButton');
            recordButton.classList.add('recording');
            recordButton.innerHTML = '<i class="fas fa-stop"></i>';
            
            document.getElementById('recordingStatus').innerHTML = '<span class="text-danger">Recording...</span>';
            
            this.showToast('Recording started', 'info');
        } catch (error) {
            console.error('Error starting recording:', error);
            this.showToast('Error starting recording: ' + error.message, 'error');
        }
    }

    stopRecording() {
        if (this.mediaRecorder) {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            const recordButton = document.getElementById('recordButton');
            recordButton.classList.remove('recording');
            recordButton.innerHTML = '<i class="fas fa-microphone"></i>';
            
            document.getElementById('recordingStatus').innerHTML = '<span class="text-success">Recording complete</span>';
            
            this.showToast('Recording stopped', 'info');
        }
    }

    playRecording() {
        const audio = document.getElementById('audioPlayback');
        if (audio.paused) {
            audio.play();
            document.getElementById('playButton').innerHTML = '<i class="fas fa-pause me-2"></i>Pause';
        } else {
            audio.pause();
            document.getElementById('playButton').innerHTML = '<i class="fas fa-play me-2"></i>Play';
        }
    }

    saveRecording() {
        if (this.currentRecording) {
            const recording = {
                ...this.currentRecording,
                id: Date.now(),
                name: `Recording ${this.recordings.length + 1}`
            };
            
            this.recordings.push(recording);
            this.updateRecordingsList();
            this.showToast('Recording saved', 'success');
        }
    }

    deleteRecording() {
        if (this.currentRecording) {
            URL.revokeObjectURL(this.currentRecording.url);
            this.currentRecording = null;
            
            document.getElementById('audioPlayback').style.display = 'none';
            document.getElementById('audioControls').style.display = 'none';
            document.getElementById('recordingStatus').innerHTML = '<span class="text-muted">Ready to record</span>';
            
            this.showToast('Recording deleted', 'info');
        }
    }

    updateRecordingsList() {
        const container = document.getElementById('recordingsList');
        
        if (this.recordings.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No recordings available</div>';
            return;
        }

        container.innerHTML = this.recordings.map(recording => `
            <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                <div>
                    <div class="fw-bold">${recording.name}</div>
                    <small class="text-muted">${new Date(recording.timestamp).toLocaleString()}</small>
                </div>
                <button class="btn btn-sm btn-outline-primary" onclick="dashboard.playStoredRecording('${recording.id}')">
                    <i class="fas fa-play"></i>
                </button>
            </div>
        `).join('');
    }

    playStoredRecording(id) {
        const recording = this.recordings.find(r => r.id == id);
        if (recording) {
            const audio = new Audio(recording.url);
            audio.play();
        }
    }

    // File upload functionality
    setupFileUpload() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }

    async handleFiles(files) {
        const progressContainer = document.getElementById('uploadProgress');
        const progressBar = progressContainer.querySelector('.progress-bar');
        
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            await this.uploadFile(file);
            
            const progress = ((i + 1) / files.length) * 100;
            progressBar.style.width = progress + '%';
        }

        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 1000);
        
        this.updateUploadedFiles();
    }

    async uploadFile(file) {
        return new Promise((resolve) => {
            // Simulate file upload
            setTimeout(() => {
                const upload = {
                    id: Date.now() + Math.random(),
                    name: file.name,
                    size: file.size,
                    type: file.type,
                    timestamp: new Date().toISOString(),
                    url: URL.createObjectURL(file)
                };
                
                this.uploads.push(upload);
                this.showToast(`File "${file.name}" uploaded successfully`, 'success');
                resolve();
            }, 500);
        });
    }

    updateUploadedFiles() {
        const container = document.getElementById('uploadedFiles');
        
        if (this.uploads.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No files uploaded yet</div>';
            return;
        }

        container.innerHTML = this.uploads.map(upload => `
            <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                <div>
                    <div class="fw-bold">${upload.name}</div>
                    <small class="text-muted">${this.formatFileSize(upload.size)} • ${new Date(upload.timestamp).toLocaleTimeString()}</small>
                </div>
                <button class="btn btn-sm btn-outline-primary" onclick="dashboard.downloadFile('${upload.id}')">
                    <i class="fas fa-download"></i>
                </button>
            </div>
        `).join('');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    downloadFile(id) {
        const upload = this.uploads.find(u => u.id == id);
        if (upload) {
            const a = document.createElement('a');
            a.href = upload.url;
            a.download = upload.name;
            a.click();
        }
    }

    // Utility functions
    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container');
        const toastId = 'toast-' + Date.now();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.id = toastId;
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    initializeToasts() {
        // Initialize bootstrap tooltips and popovers if needed
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        this.autoRefreshInterval = setInterval(() => {
            const activeSection = document.querySelector('.nav-link.active').dataset.section;
            if (activeSection === 'dashboard') {
                this.loadDashboard();
            } else if (activeSection === 'status') {
                this.checkApiStatus();
            }
        }, this.config.refreshInterval);
    }

    loadSettings() {
        const saved = localStorage.getItem('dashboardSettings');
        if (saved) {
            this.config = { ...this.config, ...JSON.parse(saved) };
        }
    }

    saveSettings() {
        this.config.plaidApiUrl = document.getElementById('plaidApiUrl').value;
        this.config.neo4jUrl = document.getElementById('neo4jUrl').value;
        this.config.refreshInterval = parseInt(document.getElementById('refreshInterval').value) * 1000;
        
        localStorage.setItem('dashboardSettings', JSON.stringify(this.config));
        this.showToast('Settings saved successfully', 'success');
        
        this.startAutoRefresh();
    }

    saveDisplaySettings() {
        const theme = document.getElementById('themeSelect').value;
        const enableNotifications = document.getElementById('enableNotifications').checked;
        const autoRefresh = document.getElementById('autoRefresh').checked;
        
        const displaySettings = { theme, enableNotifications, autoRefresh };
        localStorage.setItem('displaySettings', JSON.stringify(displaySettings));
        
        this.showToast('Display settings saved', 'success');
    }

    // API helper functions
    refreshTransactions() {
        this.loadTransactions();
        this.showToast('Transactions refreshed', 'info');
    }

    exportTransactions() {
        // This would normally make an API call to export data
        this.showToast('Export feature not yet implemented', 'warning');
    }

    viewTransactionDetails(transactionId) {
        this.showToast(`Viewing details for transaction: ${transactionId}`, 'info');
        // This would open a modal or navigate to a detail view
    }

    refreshLogs() {
        this.loadSystemLogs();
        this.showToast('Logs refreshed', 'info');
    }

    clearLogs() {
        document.getElementById('systemLogs').innerHTML = '<div class="text-muted">Logs cleared</div>';
        this.showToast('Logs cleared', 'info');
    }

    // LLM and database functionality
    async executeLLMQuery() {
        const queryInput = document.getElementById('llmQueryInput');
        const query = queryInput.value.trim();
        
        if (!query) {
            this.showToast('Please enter a query', 'warning');
            return;
        }

        const databaseId = document.getElementById('llmDatabaseSelect').value;
        
        // Show loading state
        document.getElementById('llmQueryLoading').style.display = 'block';
        document.getElementById('llmQueryResults').style.display = 'none';
        
        try {
            const response = await fetch('/api/llm/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    database_id: databaseId,
                    context: {
                        user_id: 'default_user',
                        timestamp: new Date().toISOString()
                    }
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                this.displayLLMResults(result.result);
                this.addToQueryHistory(query, result.result);
                this.showToast('Query executed successfully', 'success');
            } else {
                throw new Error(result.detail || 'Query execution failed');
            }
        } catch (error) {
            console.error('LLM Query Error:', error);
            this.showToast(`Query failed: ${error.message}`, 'error');
            
            // Show fallback results
            this.displayLLMResults({
                success: false,
                interpreted_results: `Sorry, I couldn't process your query: ${error.message}. Please try rephrasing your question or check your database connection.`,
                error_message: error.message
            });
        } finally {
            document.getElementById('llmQueryLoading').style.display = 'none';
        }
    }

    displayLLMResults(result) {
        document.getElementById('llmQueryResults').style.display = 'block';
        
        // Display interpretation
        document.getElementById('llmInterpretation').innerHTML = result.interpreted_results || 'No interpretation available';
        
        // Display generated query
        if (result.generated_query) {
            document.getElementById('llmGeneratedQuery').textContent = result.generated_query;
        }
        
        // Display execution details
        document.getElementById('llmQueryType').textContent = result.query_type || 'Unknown';
        document.getElementById('llmExecutionTime').textContent = Math.round((result.execution_time || 0) * 1000);
        document.getElementById('llmConfidence').textContent = Math.round((result.confidence_score || 0) * 100);
        
        if (result.raw_results) {
            document.getElementById('llmRowCount').textContent = Array.isArray(result.raw_results) ? result.raw_results.length : 'N/A';
        } else {
            document.getElementById('llmRowCount').textContent = '0';
        }
        
        // Display data visualization if suggested
        this.renderLLMVisualization(result);
    }

    renderLLMVisualization(result) {
        const vizContainer = document.getElementById('llmDataVisualization');
        vizContainer.innerHTML = '';
        
        if (!result.raw_results || !result.visualization_suggestions) {
            return;
        }
        
        // Create simple data table
        if (Array.isArray(result.raw_results) && result.raw_results.length > 0) {
            const table = document.createElement('table');
            table.className = 'table table-striped table-sm';
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            const firstRow = result.raw_results[0];
            
            for (const key in firstRow) {
                const th = document.createElement('th');
                th.textContent = key;
                headerRow.appendChild(th);
            }
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            result.raw_results.slice(0, 10).forEach(row => {
                const tr = document.createElement('tr');
                for (const key in firstRow) {
                    const td = document.createElement('td');
                    td.textContent = row[key] || '-';
                    tr.appendChild(td);
                }
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            
            const tableWrapper = document.createElement('div');
            tableWrapper.className = 'table-responsive';
            tableWrapper.appendChild(table);
            
            if (result.raw_results.length > 10) {
                const note = document.createElement('p');
                note.className = 'text-muted small';
                note.textContent = `Showing first 10 of ${result.raw_results.length} results`;
                tableWrapper.appendChild(note);
            }
            
            vizContainer.appendChild(tableWrapper);
        }
    }

    addToQueryHistory(query, result) {
        const historyItem = {
            id: ++this.queryCounter,
            query: query,
            timestamp: new Date().toISOString(),
            success: result.success,
            execution_time: result.execution_time
        };
        
        this.llmQueryHistory.unshift(historyItem);
        
        // Keep only last 20 queries
        if (this.llmQueryHistory.length > 20) {
            this.llmQueryHistory = this.llmQueryHistory.slice(0, 20);
        }
        
        this.updateQueryHistoryDisplay();
    }

    updateQueryHistoryDisplay() {
        const historyContainer = document.getElementById('llmQueryHistory');
        
        if (this.llmQueryHistory.length === 0) {
            historyContainer.innerHTML = '<p class="text-muted">No queries yet</p>';
            return;
        }
        
        const historyHTML = this.llmQueryHistory.map(item => `
            <div class="mb-2 p-2 border rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <small class="text-muted">${new Date(item.timestamp).toLocaleString()}</small>
                    <span class="badge ${item.success ? 'bg-success' : 'bg-danger'}">${item.success ? 'Success' : 'Failed'}</span>
                </div>
                <div class="mt-1">
                    <small class="text-truncate d-block" title="${item.query}">${item.query}</small>
                </div>
                <button class="btn btn-outline-primary btn-sm mt-1" onclick="dashboard.reuseQuery('${item.query.replace(/'/g, "\\'")}')">
                    <i class="fas fa-redo me-1"></i>Reuse
                </button>
            </div>
        `).join('');
        
        historyContainer.innerHTML = historyHTML;
    }

    reuseQuery(query) {
        document.getElementById('llmQueryInput').value = query;
        this.navigateToSection('llm-query');
    }

    // Database Management Methods
    async loadDatabaseConnections() {
        try {
            const response = await fetch('/api/database/connections');
            const result = await response.json();
            
            this.databaseConnections = result.connections || [];
            this.updateDatabaseConnectionsDisplay();
            this.updateDatabaseSelects();
        } catch (error) {
            console.error('Error loading database connections:', error);
            // Load default connections
            this.databaseConnections = [
                {
                    id: 'sqlite_default',
                    name: 'Local SQLite Database',
                    type: 'sqlite',
                    host: 'localhost',
                    port: 0,
                    database: 'data/transactions.db',
                    is_active: false
                },
                {
                    id: 'neo4j_default',
                    name: 'Neo4j Graph Database',
                    type: 'neo4j',
                    host: 'localhost',
                    port: 7687,
                    database: 'neo4j',
                    is_active: false
                }
            ];
            this.updateDatabaseConnectionsDisplay();
            this.updateDatabaseSelects();
        }
    }

    updateDatabaseConnectionsDisplay() {
        const tbody = document.getElementById('databaseConnectionsList');
        
        if (this.databaseConnections.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No database connections configured</td></tr>';
            return;
        }
        
        const connectionsHTML = this.databaseConnections.map(conn => `
            <tr>
                <td>${conn.name}</td>
                <td><span class="badge bg-secondary">${conn.type.toUpperCase()}</span></td>
                <td>${conn.host}:${conn.port}</td>
                <td>
                    <span class="status-indicator ${conn.is_active ? 'status-online' : 'status-offline'}">
                        <i class="fas fa-circle me-1"></i>
                        ${conn.is_active ? 'Connected' : 'Disconnected'}
                    </span>
                </td>
                <td>${conn.last_connected ? new Date(conn.last_connected).toLocaleString() : 'Never'}</td>
                <td>
                    <button class="btn btn-outline-primary btn-sm me-1" onclick="dashboard.testConnection('${conn.id}')">
                        <i class="fas fa-flask"></i>
                    </button>
                    <button class="btn btn-outline-success btn-sm me-1" onclick="dashboard.connectDatabase('${conn.id}')">
                        <i class="fas fa-plug"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="dashboard.removeConnection('${conn.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
        tbody.innerHTML = connectionsHTML;
        
        // Update performance metrics
        const totalConnections = this.databaseConnections.length;
        const activeConnections = this.databaseConnections.filter(c => c.is_active).length;
        
        document.getElementById('totalConnections').textContent = totalConnections;
        document.getElementById('activeConnections').textContent = activeConnections;
    }

    updateDatabaseSelects() {
        const selects = ['llmDatabaseSelect', 'directQueryDatabase'];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            const currentValue = select.value;
            
            // Clear existing options (except default ones for LLM select)
            if (selectId === 'llmDatabaseSelect') {
                // Keep default options, add custom ones
                const customOptions = select.querySelectorAll('option[data-custom]');
                customOptions.forEach(option => option.remove());
            } else {
                select.innerHTML = '<option value="">Select database...</option>';
            }
            
            // Add connection options
            this.databaseConnections.forEach(conn => {
                const option = document.createElement('option');
                option.value = conn.id;
                option.textContent = `${conn.name} (${conn.type})`;
                if (selectId !== 'llmDatabaseSelect') {
                    option.dataset.custom = 'true';
                }
                select.appendChild(option);
            });
            
            // Restore previous selection
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }

    async saveDatabaseConnection() {
        const formData = {
            name: document.getElementById('dbName').value,
            type: document.getElementById('dbType').value,
            host: document.getElementById('dbHost').value,
            port: parseInt(document.getElementById('dbPort').value),
            database: document.getElementById('dbDatabase').value,
            username: document.getElementById('dbUsername').value,
            password: document.getElementById('dbPassword').value,
            ssl: document.getElementById('dbSSL').checked
        };
        
        // Validate required fields
        if (!formData.name || !formData.type || !formData.host || !formData.database) {
            this.showToast('Please fill in all required fields', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/database/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showToast('Database connection saved successfully', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addDatabaseModal'));
                modal.hide();
                
                // Reset form
                document.getElementById('addDatabaseForm').reset();
                
                // Reload connections
                this.loadDatabaseConnections();
            } else {
                throw new Error(result.detail || 'Failed to save connection');
            }
        } catch (error) {
            console.error('Error saving database connection:', error);
            this.showToast(`Failed to save connection: ${error.message}`, 'error');
        }
    }

    async testDatabaseConnection() {
        const formData = {
            name: document.getElementById('dbName').value,
            type: document.getElementById('dbType').value,
            host: document.getElementById('dbHost').value,
            port: parseInt(document.getElementById('dbPort').value),
            database: document.getElementById('dbDatabase').value,
            username: document.getElementById('dbUsername').value,
            password: document.getElementById('dbPassword').value,
            ssl: document.getElementById('dbSSL').checked
        };
        
        // Validate required fields
        if (!formData.type || !formData.host || !formData.database) {
            this.showToast('Please fill in connection details first', 'warning');
            return;
        }
        
        const testButton = document.getElementById('testDatabaseConnection');
        const originalText = testButton.innerHTML;
        testButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Testing...';
        testButton.disabled = true;
        
        try {
            const response = await fetch('/api/database/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Connection test successful!', 'success');
            } else {
                this.showToast(`Connection test failed: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('Error testing database connection:', error);
            this.showToast(`Connection test failed: ${error.message}`, 'error');
        } finally {
            testButton.innerHTML = originalText;
            testButton.disabled = false;
        }
    }

    async executeDirectQuery() {
        const connectionId = document.getElementById('directQueryDatabase').value;
        const query = document.getElementById('directQueryText').value.trim();
        
        if (!connectionId || !query) {
            this.showToast('Please select a database and enter a query', 'warning');
            return;
        }
        
        const executeButton = document.getElementById('executeDirectQuery');
        const originalText = executeButton.innerHTML;
        executeButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Executing...';
        executeButton.disabled = true;
        
        try {
            const response = await fetch('/api/database/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    connection_id: connectionId,
                    query: query
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.result.success) {
                document.getElementById('directQueryResults').style.display = 'block';
                document.getElementById('directQueryOutput').textContent = JSON.stringify(result.result.data, null, 2);
                this.showToast(`Query executed successfully (${result.result.row_count} rows)`, 'success');
            } else {
                throw new Error(result.result?.error_message || result.detail || 'Query execution failed');
            }
        } catch (error) {
            console.error('Error executing direct query:', error);
            document.getElementById('directQueryResults').style.display = 'block';
            document.getElementById('directQueryOutput').textContent = `Error: ${error.message}`;
            this.showToast(`Query failed: ${error.message}`, 'error');
        } finally {
            executeButton.innerHTML = originalText;
            executeButton.disabled = false;
        }
    }

    async testConnection(connectionId) {
        try {
            const response = await fetch(`/api/database/test/${connectionId}`);
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Connection test successful!', 'success');
            } else {
                this.showToast(`Connection test failed: ${result.message}`, 'error');
            }
        } catch (error) {
            this.showToast(`Connection test failed: ${error.message}`, 'error');
        }
    }

    async connectDatabase(connectionId) {
        try {
            const response = await fetch(`/api/database/connect/${connectionId}`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (response.ok) {
                this.showToast('Database connected successfully', 'success');
                this.loadDatabaseConnections();
            } else {
                throw new Error(result.detail || 'Connection failed');
            }
        } catch (error) {
            this.showToast(`Connection failed: ${error.message}`, 'error');
        }
    }

    async removeConnection(connectionId) {
        if (!confirm('Are you sure you want to remove this database connection?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/database/connections/${connectionId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showToast('Database connection removed', 'success');
                this.loadDatabaseConnections();
            } else {
                throw new Error('Failed to remove connection');
            }
        } catch (error) {
            this.showToast(`Failed to remove connection: ${error.message}`, 'error');
        }
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new DashboardApp();
});

// Global functions for onclick handlers
window.dashboard = dashboard;
window.showAnalytics = (type) => dashboard.showAnalytics(type);
window.checkApiStatus = () => dashboard.checkApiStatus();
window.checkNeo4jStatus = () => dashboard.checkApiStatus();
window.saveSettings = () => dashboard.saveSettings();
window.saveDisplaySettings = () => dashboard.saveDisplaySettings();
window.refreshTransactions = () => dashboard.refreshTransactions();
window.exportTransactions = () => dashboard.exportTransactions();
window.refreshLogs = () => dashboard.refreshLogs();
window.clearLogs = () => dashboard.clearLogs();
