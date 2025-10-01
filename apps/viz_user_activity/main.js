import { Chart, registerables } from 'chart.js';

// Register Chart.js components
Chart.register(...registerables);

let chart = null;
let data = null;

// Load user activity data
async function loadData() {
    const response = await fetch('/user_activity_20_80_analysis.json');
    data = await response.json();
    return data;
}

// Update statistics display
function updateStats(activityType) {
    const activityData = data[activityType];

    document.getElementById('totalUsers').textContent = activityData.total_users.toLocaleString();
    document.getElementById('totalActivity').textContent = activityData.total_activities.toLocaleString();
    document.getElementById('avgActivity').textContent = activityData.average_per_user.toFixed(1);
    document.getElementById('medianActivity').textContent = activityData.median_activities.toLocaleString();

    // Update highlight box
    const breakpoint80 = activityData.breakpoints.users_for_80pct_activity;
    document.getElementById('highlightText').textContent =
        `${breakpoint80.user_percentage}% of users (${breakpoint80.user_count.toLocaleString()} users) account for 80% of all ${activityType}`;
}

// Create Pareto chart showing cumulative activity
function createParetoChart(activityType) {
    const ctx = document.getElementById('chart').getContext('2d');
    const activityData = data[activityType];

    // Get first 100 users from distribution sample
    const sample = activityData.distribution_sample.slice(0, 100);

    const labels = sample.map((item, idx) => idx + 1);
    const cumulativePercentages = sample.map(item => item.cumulative_activity_percentage);
    const individualCounts = sample.map(item => item.activity_count);

    // Destroy existing chart
    if (chart) {
        chart.destroy();
    }

    // Create new chart
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Cumulative % of Activity',
                    data: cumulativePercentages,
                    borderColor: 'rgba(239, 68, 68, 1)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1,
                    yAxisID: 'y'
                },
                {
                    label: 'Individual Activity Count',
                    data: individualCounts,
                    type: 'bar',
                    backgroundColor: 'rgba(59, 130, 246, 0.5)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: `Pareto Analysis: ${activityType.charAt(0).toUpperCase() + activityType.slice(1)}`,
                    font: {
                        size: 16,
                        weight: '600'
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const idx = context[0].dataIndex;
                            if (sample[idx]) {
                                return `User #${idx + 1}: ${sample[idx].user}`;
                            }
                            return `User #${idx + 1}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'User Rank (sorted by activity)'
                    },
                    ticks: {
                        maxTicksLimit: 20
                    }
                },
                y: {
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Cumulative % of Activity'
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Individual Activity Count'
                    }
                }
            }
        }
    });
}

// Create top 20 users chart
function createTop20Chart(activityType) {
    const ctx = document.getElementById('chart').getContext('2d');
    const activityData = data[activityType];
    const top20 = activityData.top_20_users;

    const labels = top20.map(u => u.user.length > 25 ? u.user.substring(0, 25) + '...' : u.user);
    const counts = top20.map(u => u.count);
    const percentages = top20.map(u => u.percentage);

    // Destroy existing chart
    if (chart) {
        chart.destroy();
    }

    // Create new chart
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: activityType === 'tags' ? 'Tags Added' : activityType === 'notes' ? 'Notes Added' : 'Comments Made',
                data: counts,
                backgroundColor: 'rgba(34, 197, 94, 0.6)',
                borderColor: 'rgba(34, 197, 94, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                title: {
                    display: true,
                    text: `Top 20 Contributors: ${activityType.charAt(0).toUpperCase() + activityType.slice(1)}`,
                    font: {
                        size: 16,
                        weight: '600'
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const idx = context[0].dataIndex;
                            return top20[idx].user;
                        },
                        label: function(context) {
                            const idx = context.dataIndex;
                            return [
                                `Count: ${context.parsed.x.toLocaleString()}`,
                                `Percentage: ${percentages[idx]}%`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Activity Count'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                },
                y: {
                    ticks: {
                        autoSkip: false
                    }
                }
            }
        }
    });
}

// Update visualization based on current settings
function updateVisualization() {
    const activityType = document.getElementById('activityType').value;
    const viewType = document.querySelector('input[name="viewType"]:checked').value;

    updateStats(activityType);

    if (viewType === 'pareto') {
        createParetoChart(activityType);
    } else {
        createTop20Chart(activityType);
    }
}

// Initialize the app
async function init() {
    await loadData();

    // Set up event listeners
    document.getElementById('activityType').addEventListener('change', updateVisualization);
    document.querySelectorAll('input[name="viewType"]').forEach(radio => {
        radio.addEventListener('change', updateVisualization);
    });

    // Create initial visualization
    updateVisualization();
}

// Start the app
init();