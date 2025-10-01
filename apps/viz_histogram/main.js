import { Chart, registerables } from 'chart.js';

// Register Chart.js components
Chart.register(...registerables);

let chart = null;
let data = null;

// Load histogram data
async function loadData() {
    // Try multiple paths for different deployment scenarios
    const paths = [
        '/histogram_data.json',      // Dev server
        './histogram_data.json',     // Same directory (GitHub Pages)
        '../histogram_data.json'     // Parent directory (GitHub Pages with dist)
    ];

    for (const path of paths) {
        try {
            const response = await fetch(path);
            if (response.ok) {
                data = await response.json();
                return data;
            }
        } catch (error) {
            continue;
        }
    }

    throw new Error('Could not load histogram_data.json from any path');
}

// Initialize the year selector
function initYearSelector(data) {
    const select = document.getElementById('yearSelect');

    // Add individual year options
    data.data.forEach(yearData => {
        const option = document.createElement('option');
        option.value = yearData.year;
        option.textContent = yearData.year;
        select.appendChild(option);
    });
}

// Calculate statistics
function calculateStats(chartData) {
    const total = chartData.reduce((sum, val) => sum + val, 0);
    const avg = Math.round(total / chartData.length);
    const peak = Math.max(...chartData);

    document.getElementById('totalComments').textContent = total.toLocaleString();
    document.getElementById('avgComments').textContent = avg.toLocaleString();
    document.getElementById('peakComments').textContent = peak.toLocaleString();
}

// Get the month for a given week number in a year
function getMonthForWeek(year, weekNumber) {
    // Create a date for Jan 1 of the year
    const jan1 = new Date(year, 0, 1);
    // Calculate days to add: (weekNumber - 1) * 7
    const daysToAdd = (weekNumber - 1) * 7;
    const weekDate = new Date(jan1.getTime() + daysToAdd * 24 * 60 * 60 * 1000);
    return weekDate.getMonth();
}

// Generate labels with month markers
function generateWeekLabels(year, weeks) {
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const labels = [];
    let lastMonth = -1;

    weeks.forEach(week => {
        const currentMonth = getMonthForWeek(year, week.week);
        if (currentMonth !== lastMonth) {
            labels.push(`${monthNames[currentMonth]} - Week ${week.week}`);
            lastMonth = currentMonth;
        } else {
            labels.push(`Week ${week.week}`);
        }
    });

    return labels;
}

// Create histogram chart
function createChart(selectedYear) {
    const ctx = document.getElementById('chart').getContext('2d');

    let labels = [];
    let chartData = [];
    let title = '';

    if (selectedYear === 'all') {
        // Show all data aggregated by year
        title = 'Comments per Year (2008-2024)';
        data.data.forEach(yearData => {
            labels.push(yearData.year.toString());
            const yearTotal = yearData.weeks.reduce((sum, week) => sum + week.comments, 0);
            chartData.push(yearTotal);
        });
    } else {
        // Show specific year data by week
        const yearData = data.data.find(d => d.year === parseInt(selectedYear));
        title = `Comments per Week in ${selectedYear}`;
        labels = generateWeekLabels(parseInt(selectedYear), yearData.weeks);
        yearData.weeks.forEach(week => {
            chartData.push(week.comments);
        });
    }

    // Update statistics
    calculateStats(chartData);

    // Destroy existing chart if it exists
    if (chart) {
        chart.destroy();
    }

    // Create new chart
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Comments',
                data: chartData,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
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
                        label: function(context) {
                            return `Comments: ${context.parsed.y.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    },
                    title: {
                        display: true,
                        text: 'Number of Comments'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: selectedYear === 'all' ? 'Year' : 'Week'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: selectedYear === 'all' ? 20 : 52
                    }
                }
            }
        }
    });
}

// Initialize the app
async function init() {
    await loadData();
    initYearSelector(data);

    // Set up event listener for year selector
    document.getElementById('yearSelect').addEventListener('change', (e) => {
        createChart(e.target.value);
    });

    // Create initial chart with all years
    createChart('all');
}

// Start the app
init();