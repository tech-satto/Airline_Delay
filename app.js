    class FlightPredictApp {
        constructor() {
            this.currentPortal = 'landing';
            this.data = null;
            this.charts = {};
            this.API_BASE_URL = 'http://127.0.0.1:8000'; // FastAPI for predictions
            this.STATS_API_BASE_URL = 'http://127.0.0.1:5000'; // Flask for data/analytics
            this.adminAuthenticated = false;
            this.init();
        }

        async init() {
            console.log('Initializing FlightPredict App with Team API Integration...');

            await this.loadData();
            await this.waitForDOM();
            this.initIcons();
            this.setupEventListeners();
            this.populateDropdowns();
            this.initializeCharts();
            this.showPortal('landing');
            this.initNeonEffects();
            await this.loadAirlineMetricsFromBackend();
            await this.loadAdminMetricsFromBackend();
            this.setupAdminAuth();

            console.log('App initialization complete with team API integration');
        }

        setupAdminAuth() {
            const adminIcon = document.getElementById('adminIcon');
            if (adminIcon) {
                adminIcon.addEventListener('click', () => {
                    const password = prompt('Enter admin password:');
                    if (password === '@admin2025') {
                        this.adminAuthenticated = true;
                        this.showPortal('admin');
                        this.showNeonNotification('Admin access granted!', 'success');
                    } else if (password !== null) {
                        this.showNeonNotification('Invalid password!', 'error');
                    }
                });
            }
        }

        waitForDOM() {
            return new Promise(resolve => {
                if (document.readyState === 'complete') {
                    resolve();
                } else {
                    window.addEventListener('load', resolve);
                }
            });
        }

        initIcons() {
            try {
                if (typeof lucide !== 'undefined' && lucide.createIcons) {
                    lucide.createIcons();
                    console.log('Lucide icons initialized');
                }
            } catch (error) {
                console.warn('Lucide icons not available:', error);
            }
        }

        initNeonEffects() {
            const pulseElements = document.querySelectorAll('.portal-icon, .metric-value, .status');
            pulseElements.forEach(element => {
                element.addEventListener('mouseenter', () => {
                    element.style.animation = 'pulse 0.6s ease-in-out';
                });
                element.addEventListener('mouseleave', () => {
                    element.style.animation = '';
                });
            });

            const buttons = document.querySelectorAll('.btn, .nav-btn');
            buttons.forEach(button => {
                button.addEventListener('click', (e) => {
                    this.createClickEffect(e.target, e.clientX, e.clientY);
                });
            });

            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {
                card.addEventListener('mouseenter', () => {
                    card.style.transition = 'all 0.3s ease-out';
                    card.style.boxShadow = '0 8px 40px rgba(0, 245, 255, 0.2)';
                });
                card.addEventListener('mouseleave', () => {
                    card.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.5)';
                });
            });

            console.log('Neon effects initialized');
        }

        createClickEffect(element, x, y) {
            const rect = element.getBoundingClientRect();
            const ripple = document.createElement('div');
            ripple.style.position = 'absolute';
            ripple.style.left = (x - rect.left) + 'px';
            ripple.style.top = (y - rect.top) + 'px';
            ripple.style.width = '0';
            ripple.style.height = '0';
            ripple.style.background = 'rgba(0, 245, 255, 0.6)';
            ripple.style.borderRadius = '50%';
            ripple.style.transform = 'translate(-50%, -50%)';
            ripple.style.animation = 'ripple 0.6s linear';
            ripple.style.pointerEvents = 'none';
            ripple.style.zIndex = '9999';

            element.style.position = 'relative';
            element.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        }

        // FIXED: Load airports/airlines from Flask backend
        async loadData() {
            try {
                const res = await fetch(`${this.STATS_API_BASE_URL}/available-options`);
                if (!res.ok) throw new Error("Failed to fetch options");
                
                const options = await res.json();

                // Save structured data
                this.data = {
                    airlines: options.airlines.map(code => ({ code, name: code })),
                    airports: [
                        ...options.origins.map(code => ({ code, name: code })),
                        ...options.destinations.map(code => ({ code, name: code }))
                    ]
                };

                console.log('âœ… Options loaded from backend:', this.data);

            } catch (error) {
                console.error('âŒ Failed to load dataset options:', error);
                // Fallback data
                this.data = {
                    airlines: [
                        { code: 'AA', name: 'AA' },
                        { code: 'DL', name: 'DL' },
                        { code: 'UA', name: 'UA' },
                        { code: 'WN', name: 'WN' }
                    ],
                    airports: [
                        { code: 'JFK', name: 'JFK' },
                        { code: 'LAX', name: 'LAX' },
                        { code: 'ORD', name: 'ORD' },
                        { code: 'ATL', name: 'ATL' }
                    ]
                };
            }
        }

        async loadAirlineMetricsFromBackend() {
            // Keep original fallback metrics
            this.adminMetrics = [
                { month: 'Jan', accuracy: 87.2, auc: 0.85 },
                { month: 'Feb', accuracy: 88.1, auc: 0.86 },
                { month: 'Mar', accuracy: 89.5, auc: 0.88 },
                { month: 'Apr', accuracy: 90.2, auc: 0.89 },
                { month: 'May', accuracy: 89.8, auc: 0.88 },
                { month: 'Jun', accuracy: 91.1, auc: 0.90 },
                { month: 'Jul', accuracy: 92.3, auc: 0.91 }
            ];
        }

        async loadAdminMetricsFromBackend() {
            // Keep original fallback metrics
            this.adminMetrics = [
                { month: 'Jan', accuracy: 87.2, auc: 0.85 },
                { month: 'Feb', accuracy: 88.1, auc: 0.86 },
                { month: 'Mar', accuracy: 89.5, auc: 0.88 },
                { month: 'Apr', accuracy: 90.2, auc: 0.89 },
                { month: 'May', accuracy: 89.8, auc: 0.88 },
                { month: 'Jun', accuracy: 91.1, auc: 0.90 },
                { month: 'Jul', accuracy: 92.3, auc: 0.91 }
            ];
        }

        setupEventListeners() {
            console.log('Setting up event listeners with team API integration...');

            const portalElements = document.querySelectorAll('[data-portal]');
            console.log(`Found ${portalElements.length} portal elements`);

            portalElements.forEach(element => {
                element.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();

                    const portal = element.getAttribute('data-portal');
                    console.log(`Clicked portal element: ${portal}`);

                    if (portal === 'admin' && !this.adminAuthenticated) {
                        const password = prompt('Enter admin password:');
                        if (password === '@admin2025') {
                            this.adminAuthenticated = true;
                            this.showPortal('admin');
                            this.showNeonNotification('Admin access granted!', 'success');
                        } else if (password !== null) {
                            this.showNeonNotification('Invalid password!', 'error');
                        }
                        return;
                    }

                    if (portal) {
                        this.showPortal(portal);

                        element.style.boxShadow = '0 0 30px rgba(0, 245, 255, 0.8)';
                        setTimeout(() => {
                            element.style.boxShadow = '';
                        }, 300);
                    }
                });
            });

            const logoElement = document.querySelector('.logo[data-portal="landing"]');
            if (logoElement) {
                console.log('Logo element found, adding click listener');
                logoElement.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Logo clicked - navigating to landing');
                    this.showPortal('landing');
                });
            }

            const navButtons = document.querySelectorAll('.nav-btn[data-portal]');
            console.log(`Found ${navButtons.length} nav buttons`);

            navButtons.forEach(button => {
                const portal = button.getAttribute('data-portal');
                console.log(`Setting up nav button for: ${portal}`);

                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log(`Nav button clicked: ${portal}`);
                    
                    if (portal === 'admin' && !this.adminAuthenticated) {
                        const password = prompt('Enter admin password:');
                        if (password === '@admin2025') {
                            this.adminAuthenticated = true;
                            this.showPortal('admin');
                            this.showNeonNotification('Admin access granted!', 'success');
                        } else if (password !== null) {
                            this.showNeonNotification('Invalid password!', 'error');
                        }
                        return;
                    }
                    
                    this.showPortal(portal);
                });
            });

            const flightForm = document.getElementById('flightSearchForm');
            if (flightForm) {
                console.log('Flight search form found');
                flightForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Flight search form submitted - calling team API');
                    this.handleFlightSearchTeamAPI();
                });
            }

            const airlineSelect = document.getElementById('airlineSelect');
            if (airlineSelect) {
                console.log('Airline selector found');
                airlineSelect.addEventListener('change', (e) => {
                    console.log(`Airline changed to: ${e.target.value}`);
                    this.updateAirlineMetrics(e.target.value);

                    e.target.style.boxShadow = '0 0 15px rgba(0, 245, 255, 0.5)';
                    setTimeout(() => {
                        e.target.style.boxShadow = '';
                    }, 500);
                });
            }

            const userAirlineSelect = document.getElementById('userAirlineSelect');
            if (userAirlineSelect) {
                console.log('User airline selector found');
                userAirlineSelect.addEventListener('change', (e) => {
                    console.log(`User airline changed to: ${e.target.value}`);
                    this.updateAirlineMetrics(e.target.value);

                    e.target.style.boxShadow = '0 0 15px rgba(0, 245, 255, 0.5)';
                    setTimeout(() => {
                        e.target.style.boxShadow = '';
                    }, 500);
                });
            }

            const retrainBtn = document.getElementById('retrainBtn');
            if (retrainBtn) {
                console.log('Retrain button found');
                retrainBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log('Retrain button clicked');
                    this.handleRetrain();
                });
            }

            const rescheduleBtn = document.getElementById('rescheduleBtn');
            if (rescheduleBtn) {
                console.log('Reschedule button found');
                rescheduleBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log('Reschedule button clicked');
                    this.handleCabReschedule();
                });
            }

            const routeSearchBtn = document.getElementById('routeSearchBtn');
            if (routeSearchBtn) {
                routeSearchBtn.addEventListener('click', () => this.handleRouteSearch());
            }

            console.log('Event listeners setup complete');
        }

        showPortal(portalId) {
            console.log(`SHOWING portal: ${portalId} with neon transition`);

            document.querySelectorAll('.portal').forEach(portal => {
                portal.classList.remove('active');
            });

            const targetPortal = document.getElementById(portalId);
            if (targetPortal) {
                targetPortal.classList.add('active');
                console.log(`Portal ${portalId} activated successfully`);
            } else {
                console.error(`Portal ${portalId} not found in DOM`);
                return;
            }

            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
                const btnPortal = btn.getAttribute('data-portal');
                if (btnPortal === portalId) {
                    btn.classList.add('active');
                    console.log(`Nav button ${btnPortal} set to active`);
                }
            });

            this.currentPortal = portalId;

            setTimeout(() => {
                if (portalId === 'airline') {
                    console.log('Initializing airline charts');
                    this.updateAirlineCharts();
                } else if (portalId === 'admin') {
                    console.log('Initializing admin charts');
                    this.updateAdminCharts();
                }
            }, 300);

            console.log(`Portal navigation to ${portalId} completed`);
        }

        async handleRouteSearch() {
        const origin = document.getElementById('routeOriginSelect').value;
        const destination = document.getElementById('routeDestinationSelect').value;
        const airline = document.getElementById('airlineSelect').value; // <-- the airline selected in Performance Overview

        // Define containers before use
        const distributionContainer = document.getElementById('routeDistributionContainer');
        const totalsContainer = document.getElementById('routeTotalsContainer');
        if (!distributionContainer || !totalsContainer) {
            this.showNeonNotification('Route Distribution containers not found in DOM.', 'error');
            return;
        }

        if (!origin || !destination) {
            this.showNeonNotification('Please select both an origin and a destination.', 'warning');
            return;
        }
        if (origin === destination) {
            this.showNeonNotification('Origin and destination cannot be the same.', 'error');
            return;
        }

        try {
            const routeUrl = `${this.STATS_API_BASE_URL}/route-performance?origin=${origin}&destination=${destination}${airline ? `&airline=${airline}` : ''}`;
            const response = await fetch(routeUrl);
            if (!response.ok) {
                throw new Error(`No data found for route ${origin} to ${destination}`);
            }
            const routeData = await response.json();

            // Update the delay distribution metric cards
            distributionContainer.innerHTML = `
                <div class="metric-card">
                    <span class="metric-label">0-15 min</span>
                    <span class="metric-value">${routeData.delay_distribution['0-15min'] ?? '--'}</span>
                </div>
                <div class="metric-card">
                    <span class="metric-label">15-60 min</span>
                    <span class="metric-value">${routeData.delay_distribution['15-60min'] ?? '--'}</span>
                </div>
                <div class="metric-card">
                    <span class="metric-label">60+ min</span>
                    <span class="metric-value">${routeData.delay_distribution['60+min'] ?? '--'}</span>
                </div>
            `;

            // Update the total stats display (all stats)
            totalsContainer.innerHTML = `
                <div class="financial-metric">
                    <span class="metric-label">Total Flights (This Airline)</span>
                    <span class="metric-value">${routeData.total_flights ?? '--'}</span>
                </div>
                <div class="financial-metric">
                    <span class="metric-label">Airlines on Route</span>
                    <span class="metric-value">${routeData.num_airlines ?? '--'}</span>
                </div>
                <div class="financial-metric">
                    <span class="metric-label">Avg Arrival Delay</span>
                    <span class="metric-value">${routeData.avg_arrival_delay !== undefined ? routeData.avg_arrival_delay + " min" : '--'}</span>
                </div>
                <div class="financial-metric">
                    <span class="metric-label">Avg Departure Delay</span>
                    <span class="metric-value">${routeData.avg_departure_delay !== undefined ? routeData.avg_departure_delay + " min" : '--'}</span>
                </div>
            `;

        } catch (error) {
            this.showNeonNotification(error.message, 'error');
            console.error('Failed to load route performance:', error);
        }
    }

        populateDropdowns() {
            console.log('Populating dropdowns with team data...');

            if (!this.data) return;

            // Populate airline dropdowns
            const airlineSelects = [
                document.getElementById("userAirlineSelect"),
                document.getElementById("airlineSelect")
            ];

            airlineSelects.forEach(select => {
                if (select) {
                    select.innerHTML = `<option value="">Select Airline</option>`;
                    this.data.airlines.forEach(airline => {
                        select.innerHTML += `<option value="${airline.code}">${airline.name}</option>`;
                    });
                }
            });

            // Populate airport dropdowns
            const originSelects = [
                document.getElementById("originSelect"),
                document.getElementById("routeOriginSelect")
            ];
            const destinationSelects = [
                document.getElementById("destinationSelect"),
                document.getElementById("routeDestinationSelect")
            ];

            originSelects.forEach(select => {
                if (select) {
                    select.innerHTML = `<option value="">Select Origin</option>`;
                    this.data.airports.forEach(airport => {
                        select.innerHTML += `<option value="${airport.code}">${airport.name}</option>`;
                    });
                }
            });

            destinationSelects.forEach(select => {
                if (select) {
                    select.innerHTML = `<option value="">Select Destination</option>`;
                    this.data.airports.forEach(airport => {
                        select.innerHTML += `<option value="${airport.code}">${airport.name}</option>`;
                    });
                }
            });

            console.log('Dropdowns populated with team data');
        }

        // FIXED: Updated to use FastAPI backend
        // Fetch prediction from FastAPI and update dashboard for traveler
        async handleFlightSearchTeamAPI() {
            console.log('Handling flight search with FastAPI integration...');

            // Get form input elements
            const originSelect = document.getElementById('originSelect');
            const destinationSelect = document.getElementById('destinationSelect');
            const dateInput = document.getElementById('flightDate');
            const timeSelect = document.getElementById('flightTime');
            const airlineSelect = document.getElementById('userAirlineSelect');

            // Extract values
            const origin = originSelect?.value;
            const destination = destinationSelect?.value;
            const date = dateInput?.value;
            const timeStr = timeSelect?.value;
            const airlineCode = airlineSelect?.value;

            // Validate required fields
            if (!origin || !destination || !date || !timeStr || !airlineCode) {
                this.showNeonNotification('Please fill out all required fields including airline', 'error');
                return;
            }
            if (origin === destination) {
                this.showNeonNotification('Origin and destination cannot be the same', 'error');
                return;
            }

            // Parse date
            const [year, month, day] = date.split('-').map(Number);
            // Parse time as HHMM integer
            const [hours, minutes] = timeStr.split(':').map(Number);
            const scheduledDeparture = hours * 100 + minutes;

            const payload = {
            date: `${year}-${month}-${day}`,
            airline: airlineCode,
            origin: origin, // instead of origin_airport
            destination: destination, // instead of destination_airport
            sched_departure: scheduledDeparture // instead of scheduled_departure
        };


            console.log('Sending payload to FastAPI:', payload);

            try {
                this.showModal('loadingModal', 'Analyzing flight data with AI...');

                const response = await fetch(`${this.API_BASE_URL}/predict`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${response.status} message: ${errorText}`);
                }

                const data = await response.json();
                console.log('Received FastAPI response:', data);

                // Use the full data object!
                this.hideModal('loadingModal');
                this.displayTeamAPIPrediction(data, origin, destination);


                // Optionally, reload route statistics
                await this.displayRouteStatistics(origin, destination, airlineCode);

            } catch (error) {
                this.hideModal('loadingModal');
                this.showNeonNotification('API request failed: ' + error.message, 'error');
                console.error('Error calling FastAPI:', error);
                this.displayDemoPrediction(origin, destination, airlineCode);
            }
        }

        // Update dashboard with prediction results and alternative flights
        displayTeamAPIPrediction(data, origin, destination) {
            if (!data) {
            console.error('displayTeamAPIPrediction called with undefined data!');
            return;
        }
            const predictionCard = document.getElementById('predictionResults');
            const probabilityElement = document.getElementById('delayProbability');
            const expectedDelayElement = document.getElementById('expectedDelay');
            const statusElement = document.getElementById('predictionStatus');
            const alternativesCard = document.getElementById('alternativesCard');
            const alternativesList = document.getElementById('alternativesList');
            const predictionTextEl = document.getElementById('predictionText');
            const confidenceScoreEl = document.getElementById('confidenceScore');

            if (!(predictionCard && probabilityElement && expectedDelayElement && statusElement)) {
                console.error('Prediction result elements not found');
                return;
            }

            // Extract result values
            console.log("Display function called with data:", data);
            const probability = data.delay_probability ?? data.prob_delay ?? 0;
            const confidence = data.confidence ?? 0.85;
            const predictionText = data.prediction_text ?? (probability > 0.5 ? 'Delayed' : 'On Time');
            const isDelayed = data.is_delayed ?? (probability > 0.5);
            const expectedDelay = Math.floor(probability * 60) + 10;

            // Display prediction info
            probabilityElement.textContent = `${Math.round(probability * 100)}%`;
            expectedDelayElement.textContent = `${expectedDelay} min`;
            if (predictionTextEl) predictionTextEl.textContent = predictionText;
            if (confidenceScoreEl) confidenceScoreEl.textContent = `${Math.round(confidence * 100)}%`;

            // Add pulse animation
            [probabilityElement, expectedDelayElement].forEach(el => {
                if (el) el.style.animation = 'pulse 1s ease-in-out 3';
            });

            // Set risk class and status message
            let statusClass = 'status--success', statusText = 'Low Risk';
            if (probability > 0.6) { statusClass = 'status--error'; statusText = 'High Risk'; }
            else if (probability > 0.3) { statusClass = 'status--warning'; statusText = 'Medium Risk'; }

            statusElement.innerHTML = `<span class="status ${statusClass}">${statusText}</span>`;

            // Reveal prediction card with fade-in effect
            predictionCard.style.opacity = '0';
            predictionCard.classList.remove('hidden');
            predictionCard.style.transform = 'translateY(20px)';
            setTimeout(() => {
                predictionCard.style.transition = 'all 0.5s ease-out';
                predictionCard.style.opacity = '1';
                predictionCard.style.transform = 'translateY(0)';
            }, 100);

            // Display alternative flights
            if (alternativesCard && alternativesList && Array.isArray(data.alternative_flights) && data.alternative_flights.length > 0) {
                alternativesList.innerHTML = data.alternative_flights.map(flight => {
                    const depStr = flight.departure.toString().padStart(4, '0');
                    const depFormatted = `${depStr.slice(0, 2)}:${depStr.slice(2)}`;
                    let riskClass = 'risk-low', riskText = 'Low Risk';
                    if (flight.prob_delay >= 0.4) { riskClass = 'risk-high'; riskText = 'High Risk'; }
                    else if (flight.prob_delay >= 0.2) { riskClass = 'risk-medium'; riskText = 'Medium Risk'; }
                    return `
                        <div class="alternative-flight">
                            <div class="flight-info">
                                <div class="flight-route">${flight.airline} - ${depFormatted}</div>
                                <div class="flight-details">${origin} &rarr; ${destination} &bull; ${Math.round(flight.prob_delay * 100)}% delay risk</div>
                            </div>
                            <div class="risk-score">
                                <div class="risk-indicator ${riskClass}"></div>
                                <span>${riskText}</span>
                            </div>
                        </div>
                    `;
                }).join('');
                alternativesCard.style.opacity = '0';
                alternativesCard.classList.remove('hidden');
                setTimeout(() => {
                    alternativesCard.style.transition = 'all 0.5s ease-out';
                    alternativesCard.style.opacity = '1';
                }, 200);
            } else if (alternativesList) {
                alternativesList.innerHTML = '<p>No alternative flights available for this route.</p>';
                if (alternativesCard) alternativesCard.classList.remove('hidden');
            }

            // Optionally show cab booking card for risky flights
            if (probability > 0.3) {
                const cabCard = document.getElementById('cabCard');
                if (cabCard) {
                    cabCard.style.opacity = '0';
                    cabCard.classList.remove('hidden');
                    setTimeout(() => {
                        cabCard.style.transition = 'all 0.5s ease-out';
                        cabCard.style.opacity = '1';
                    }, 100);
                }
            }
        }

        // Show route performance stats in traveler portal
        async displayRouteStatistics(origin, destination, selectedAirline) {
            try {
                const response = await fetch(`${this.STATS_API_BASE_URL}/route-performance?origin=${origin}&destination=${destination}`);
                if (!response.ok) throw new Error(`Failed to fetch route statistics`);
                const routeData = await response.json();

                // Get DOM elements
                const routeAirlinesEl = document.getElementById('routeAirlines');
                const airlineListEl = document.getElementById('airlineList');
                const totalFlightsEl = document.getElementById('totalFlights');
                const selectedAirlineFlightsEl = document.getElementById('selectedAirlineFlights');
                const onTimeBarEl = document.getElementById('onTimeBar');
                const delayedBarEl = document.getElementById('delayedBar');

                // Render stats
                if (routeAirlinesEl && this.data) {
                    const airlinesOnRoute = this.data.airlines.slice(0, 4);
                    routeAirlinesEl.textContent = airlinesOnRoute.length;
                    if (airlineListEl) airlineListEl.textContent = airlinesOnRoute.map(a => a.code).join(', ');
                }
                if (totalFlightsEl) totalFlightsEl.textContent = routeData.total_flights || 0;
                if (selectedAirlineFlightsEl) {
                    const estimatedFlights = Math.floor((routeData.total_flights || 0) * 0.25);
                    selectedAirlineFlightsEl.textContent = estimatedFlights;
                }

                // Bar distribution
                const totalDelayFlights = (routeData.delay_distribution?.['0-15min'] || 0)
                                    + (routeData.delay_distribution?.['15-60min'] || 0)
                                    + (routeData.delay_distribution?.['60+min'] || 0);
                const totalFlights = routeData.total_flights || 1;
                const onTimeFlights = totalFlights - totalDelayFlights;

                const onTimePercent = Math.max(0, Math.floor((onTimeFlights / totalFlights) * 100));
                const delayedPercent = Math.min(100, 100 - onTimePercent);

                if (onTimeBarEl) {
                    onTimeBarEl.style.width = `${onTimePercent}%`;
                    onTimeBarEl.textContent = `On Time (${onTimePercent}%)`;
                }
                if (delayedBarEl) {
                    delayedBarEl.style.width = `${delayedPercent}%`;
                    delayedBarEl.textContent = `Delayed (${delayedPercent}%)`;
                }

                const routeStatsCard = document.getElementById('routeStatsCard');
                if (routeStatsCard) routeStatsCard.classList.remove('hidden');
            } catch (error) {
                console.error('Failed to load route statistics:', error);
            }
        }

        // Create demo (random) prediction for fallback
        displayDemoPrediction(origin, destination, airline) {
            console.log('Displaying demo prediction...');
            const demoData = {
                prob_delay: Math.random() * 0.6,
                delay_probability: Math.random() * 0.6,
                confidence: 0.85 + Math.random() * 0.15,
                prediction_text: Math.random() > 0.5 ? 'Delayed' : 'On Time',
                is_delayed: Math.random() > 0.5,
                alternative_flights: [
                    { airline: "DL", departure: 959, prob_delay: Math.random() * 0.3 },
                    { airline: "AA", departure: 715, prob_delay: Math.random() * 0.3 },
                    { airline: "UA", departure: 1100, prob_delay: Math.random() * 0.3 }
                ]
            };
            this.displayTeamAPIPrediction(demoData, origin, destination);
        }

        // Reschedule cab animation
        handleCabReschedule() {
            const cabStatus = document.getElementById('cabStatus');
            const rescheduleBtn = document.getElementById('rescheduleBtn');
            if (!cabStatus) return;
            rescheduleBtn.style.opacity = '0.7';
            rescheduleBtn.disabled = true;
            setTimeout(() => {
                cabStatus.innerHTML = '<span class="status status--success">Cab rescheduled for 3:15 PM</span>';
                rescheduleBtn.style.opacity = '1';
                rescheduleBtn.disabled = false;
                this.showNeonNotification('Cab successfully rescheduled!', 'success');
            }, 1500);
        }


        // FIXED: Updated to use Flask backend for airline stats
        async updateAirlineMetrics(airlineCode) {
            const metricsContainer = document.getElementById('airlineMetrics');
            const rankingContainer = document.getElementById('rankingMetrics');
            if (!metricsContainer || !rankingContainer) return;

            // Reset view when no airline is selected
            if (!airlineCode) {
                metricsContainer.innerHTML = `
                    <div class="metric-card"><span class="metric-label">On-Time Performance</span><span class="metric-value">--</span></div>
                    <div class="metric-card"><span class="metric-label">Avg Arrival Delay</span><span class="metric-value">--</span></div>
                    <div class="metric-card"><span class="metric-label">Avg Departure Delay</span><span class="metric-value">--</span></div>
                    <div class="metric-card"><span class="metric-label">Monthly Flights</span><span class="metric-value">--</span></div>
                `;
                rankingContainer.innerHTML = `
                    <div class="financial-metric"><span class="metric-label">Rank by Arrival Delay</span><span class="metric-value">--</span></div>
                    <div class="financial-metric"><span class="metric-label">Rank by Departure Delay</span><span class="metric-value">--</span></div>
                `;
                if (this.charts.delayCauseChart) this.charts.delayCauseChart.destroy();
                return;
            }

            try {
                const response = await fetch(`${this.STATS_API_BASE_URL}/airline-delay-stats?airline=${airlineCode}`);
                if (!response.ok) {
                    throw new Error(`API request failed with status ${response.status}`);
                }
                const stats = await response.json();

                // Calculate On-Time Performance from delay causes
                const totalDelayPercentage = Object.values(stats.delays_by_cause).reduce((sum, value) => sum + value, 0);
                const onTimePerformance = Math.max(0, 100 - totalDelayPercentage);

                metricsContainer.innerHTML = `
                    <div class="metric-card">
                        <span class="metric-label">On-Time Performance</span>
                        <span class="metric-value">${onTimePerformance.toFixed(1)}%</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-label">Avg Arrival Delay</span>
                        <span class="metric-value">${stats.avg_arrival_delay.toFixed(1)} min</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-label">Avg Departure Delay</span>
                        <span class="metric-value">${stats.avg_departure_delay.toFixed(1)} min</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-label">Monthly Flights</span>
                        <span class="metric-value">${stats.total_flights.toLocaleString()}</span>
                    </div>
                `;

                rankingContainer.innerHTML = `
                    <div class="financial-metric">
                        <span class="metric-label">Rank by Arrival Delay</span>
                        <span class="metric-value">${stats.ranking.rank_by_arrival_delay} / ${stats.ranking.total_airlines}</span>
                    </div>
                    <div class="financial-metric">
                        <span class="metric-label">Rank by Departure Delay</span>
                        <span class="metric-value">${stats.ranking.rank_by_departure_delay} / ${stats.ranking.total_airlines}</span>
                    </div>
                `;
                
                // FIXED: Call function to create/update the doughnut chart
                this.createDelayCauseChart(stats.delays_by_cause);

            } catch (error) {
                console.error('Failed to load airline stats:', error);
                this.showNeonNotification(`Could not load stats for ${airlineCode}.`, 'error');
            }
        }

        initializeCharts() {
            this.charts = {};
        }

        updateAirlineCharts() {
            setTimeout(() => {
                this.createRouteChart();
            }, 300);
        }

        // FIXED: Delay cause chart with proper Chart.js integration
        createDelayCauseChart(delayData) {
            const ctx = document.getElementById('delayCauseChart');
            if (!ctx) return;

            if (this.charts.delayCauseChart) {
                this.charts.delayCauseChart.destroy();
            }

            const labels = Object.keys(delayData).map(key =>
                key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
            );
            const data = Object.values(delayData);

            this.charts.delayCauseChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Delay Cause %',
                        data: data,
                        backgroundColor: [
                            '#00f5ff', // Neon Blue
                            '#ff10f0', // Neon Pink
                            '#39ff14', // Neon Green
                            '#ffac1c', // Neon Orange
                            '#bf00ff'  // Neon Purple
                        ],
                        borderColor: '#1a1a1a',
                        borderWidth: 3,
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                color: '#ffffff',
                                font: { size: 12 },
                                boxWidth: 20
                            }
                        }
                    }
                }
            });
        }

        createTimeSlotChart() {
            const ctx = document.getElementById('timeSlotChart');
            if (!ctx) return;

            try {
                if (this.charts.timeSlotChart) {
                    this.charts.timeSlotChart.destroy();
                }

                const timeSlots = [
                    { time_period: "00:00-01:00", delay_probability: 0.37, avg_delay_minutes: 47 },
                    { time_period: "01:00-02:00", delay_probability: 0.41, avg_delay_minutes: 58 },
                    { time_period: "06:00-07:00", delay_probability: 0.31, avg_delay_minutes: 56 },
                    { time_period: "12:00-13:00", delay_probability: 0.21, avg_delay_minutes: 23 },
                    { time_period: "18:00-19:00", delay_probability: 0.35, avg_delay_minutes: 45 }
                ];

                this.charts.timeSlotChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: timeSlots.map(t => t.time_period),
                        datasets: [{
                            label: 'Delay Probability',
                            data: timeSlots.map(t => t.delay_probability * 100),
                            borderColor: '#ff10f0',
                            backgroundColor: 'rgba(255, 16, 240, 0.1)',
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#ff10f0',
                            pointBorderColor: '#ff10f0',
                            pointRadius: 5,
                            pointHoverRadius: 8
                        }, {
                            label: 'Average Delay (min)',
                            data: timeSlots.map(t => t.avg_delay_minutes),
                            borderColor: '#bf00ff',
                            backgroundColor: 'rgba(191, 0, 255, 0.1)',
                            fill: false,
                            tension: 0.4,
                            yAxisID: 'y1',
                            pointBackgroundColor: '#bf00ff',
                            pointBorderColor: '#bf00ff',
                            pointRadius: 5,
                            pointHoverRadius: 8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#ffffff',
                                    font: { size: 12 }
                                }
                            }
                        },
                        scales: {
                            x: {
                                ticks: { color: '#ffffff' },
                                grid: { color: 'rgba(0, 245, 255, 0.2)' }
                            },
                            y: {
                                ticks: { color: '#ffffff' },
                                grid: { color: 'rgba(0, 245, 255, 0.2)' }
                            },
                            y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                ticks: { color: '#ffffff' },
                                grid: { drawOnChartArea: false }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Error creating time slot chart:', error);
            }
        }

        updateAdminCharts() {
            setTimeout(() => {
                this.createModelChart();
            }, 300);
        }

        createModelChart() {
            const ctx = document.getElementById('modelChart');
            if (!ctx) return;

            try {
                if (this.charts.modelChart) {
                    this.charts.modelChart.destroy();
                }

                let labels, accuracyData, aucData;

                if (this.adminMetrics && Array.isArray(this.adminMetrics)) {
                    labels = this.adminMetrics.map(m => m.month);
                    accuracyData = this.adminMetrics.map(m => m.accuracy);
                    aucData = this.adminMetrics.map(m => m.auc);
                } else {
                    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'];
                    accuracyData = [87.2, 88.1, 89.5, 90.2, 89.8, 91.1, 92.3];
                    aucData = [0.85, 0.86, 0.88, 0.89, 0.88, 0.90, 0.91];
                }

                this.charts.modelChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Model Accuracy (%)',
                            data: accuracyData,
                            borderColor: '#00f5ff',
                            backgroundColor: 'rgba(0, 245, 255, 0.1)',
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#00f5ff',
                            pointBorderColor: '#00f5ff',
                            pointRadius: 6,
                            pointHoverRadius: 10
                        }, {
                            label: 'AUC Score',
                            data: aucData.map(v => v * 100),
                            borderColor: '#39ff14',
                            backgroundColor: 'rgba(57, 255, 20, 0.1)',
                            fill: false,
                            tension: 0.4,
                            pointBackgroundColor: '#39ff14',
                            pointBorderColor: '#39ff14',
                            pointRadius: 6,
                            pointHoverRadius: 10
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#ffffff',
                                    font: { size: 12 }
                                }
                            }
                        },
                        scales: {
                            x: {
                                ticks: { color: '#ffffff' },
                                grid: { color: 'rgba(0, 245, 255, 0.2)' }
                            },
                            y: {
                                ticks: { color: '#ffffff' },
                                grid: { color: 'rgba(0, 245, 255, 0.2)' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Error creating model chart:', error);
            }
        }

        async handleRetrain() {
            const button = document.getElementById('retrainBtn');
            if (!button) return;

            const originalHTML = button.innerHTML;

            button.innerHTML = '<div class="loading-spinner" style="width: 16px; height: 16px; margin-right: 8px; display: inline-block;"></div>Retraining...';
            button.disabled = true;

            await new Promise(resolve => setTimeout(resolve, 3000));

            button.innerHTML = originalHTML;
            button.disabled = false;

            const versionElements = document.querySelectorAll('.model-metric .metric-value');
            versionElements.forEach(element => {
                if (element.textContent === 'v2.3.1') {
                    element.textContent = 'v2.3.2';
                    element.style.animation = 'pulse 1s ease-in-out 3';
                }
            });

            await this.loadAdminMetricsFromBackend();
            if (this.currentPortal === 'admin') {
                this.updateAdminCharts();
            }

            this.showNeonNotification('Model retraining completed successfully!', 'success');
        }

        showModal(modalId, message) {
            const modal = document.getElementById(modalId);
            const messageElement = document.getElementById('loadingMessage');

            if (modal) {
                if (messageElement && message) {
                    messageElement.textContent = message;
                }
                modal.style.opacity = '0';
                modal.classList.remove('hidden');
                setTimeout(() => {
                    modal.style.transition = 'opacity 0.3s ease-out';
                    modal.style.opacity = '1';
                }, 50);
            }
        }

        hideModal(modalId) {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.style.opacity = '0';
                setTimeout(() => {
                    modal.classList.add('hidden');
                }, 300);
            }
        }

        showNeonNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.className = `alert alert--${type}`;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1001;
                max-width: 400px;
                background: rgba(10, 10, 10, 0.95);
                backdrop-filter: blur(20px);
                border: 2px solid var(--neon-blue);
                box-shadow: 0 0 30px rgba(0, 245, 255, 0.5);
                animation: slideInRight 0.5s ease-out;
                padding: 15px 20px;
                border-radius: 8px;
                color: white;
            `;

            const iconMap = {
                success: 'check-circle',
                error: 'x-circle',
                warning: 'alert-triangle',
                info: 'info'
            };

            notification.innerHTML = `
                <i data-lucide="${iconMap[type]}" class="alert-icon" style="margin-right: 10px;"></i>
                <div class="alert-content" style="display: inline;">
                    <span class="alert-message">${message}</span>
                </div>
            `;

            document.body.appendChild(notification);
            this.initIcons();

            setTimeout(() => {
                notification.style.animation = 'slideOutRight 0.5s ease-out';
                setTimeout(() => {
                    notification.remove();
                }, 500);
            }, 3000);
        }
    }

    // Add CSS animations for notifications
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }

        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
                filter: drop-shadow(0 0 5px currentColor);
            }
            50% {
                transform: scale(1.05);
                filter: drop-shadow(0 0 20px currentColor);
            }
        }

        @keyframes ripple {
            to {
                width: 60px;
                height: 60px;
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // Global app instance
    let app = null;

    // Initialize the application
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM loaded, initializing team API integrated app...');
        app = new FlightPredictApp();
    });

    // Fallback initialization
    window.addEventListener('load', () => {
        if (!app) {
            console.log('Fallback initialization...');
            app = new FlightPredictApp();
        }
    }); 

    

    