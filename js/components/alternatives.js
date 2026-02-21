// Alternatives Component
const AlternativesComponent = {
    shoppingList: [],
    currentCategory: '',

    render() {
        return `
            <div class="section-container">
                <div class="row">
                    <div class="col-lg-8">
                        <div class="card">
                            <div class="card-header">
                                <h3><i class="fas fa-exchange-alt"></i> Find Safer Alternatives</h3>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <label class="form-label">Product Category</label>
                                        <select class="form-select" id="categorySelect">
                                            <option value="">Select category...</option>
                                            <option value="cosmetics">Cosmetics</option>
                                            <option value="personal-care">Personal Care</option>
                                            <option value="cleaning">Cleaning Products</option>
                                            <option value="food-packaging">Food Packaging</option>
                                            <option value="baby-care">Baby Care</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Current Product Score</label>
                                        <input type="number" class="form-control" id="currentScore" 
                                               placeholder="0-100" min="0" max="100" value="45">
                                    </div>
                                </div>

                                <div class="row mt-3">
                                    <div class="col-md-6">
                                        <label class="form-label">Price Preference</label>
                                        <select class="form-select" id="pricePreference">
                                            <option value="">Any</option>
                                            <option value="budget">Budget</option>
                                            <option value="mid-range">Mid-range</option>
                                            <option value="premium">Premium</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Region</label>
                                        <select class="form-select" id="regionSelect">
                                            <option value="">Any</option>
                                            <option value="kerala">Kerala</option>
                                            <option value="karnataka">Karnataka</option>
                                            <option value="tamil-nadu">Tamil Nadu</option>
                                            <option value="maharashtra">Maharashtra</option>
                                        </select>
                                    </div>
                                </div>

                                <button class="btn btn-primary btn-lg w-100 mt-3" id="searchBtn">
                                    <i class="fas fa-search"></i> Search Alternatives
                                </button>
                            </div>
                        </div>

                        <div id="alternativesResults" class="mt-4" style="display: none;">
                            <h4>Safer Alternatives</h4>
                            <div id="alternativesList"></div>
                        </div>
                    </div>

                    <div class="col-lg-4">
                        <div class="card">
                            <div class="card-header">
                                <h4><i class="fas fa-shopping-cart"></i> Shopping List</h4>
                            </div>
                            <div class="card-body">
                                <div id="shoppingListContainer">
                                    <p class="text-muted text-center">Your shopping list is empty</p>
                                </div>
                                <button class="btn btn-success w-100 mt-3" id="exportListBtn" style="display: none;">
                                    <i class="fas fa-download"></i> Export List
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init() {
        document.getElementById('searchBtn').addEventListener('click', () => this.searchAlternatives());
        document.getElementById('exportListBtn').addEventListener('click', () => this.exportShoppingList());
        this.loadShoppingList();
    },

    async searchAlternatives() {
        const category = document.getElementById('categorySelect').value;
        const currentScore = parseFloat(document.getElementById('currentScore').value);
        const pricePreference = document.getElementById('pricePreference').value || null;
        const region = document.getElementById('regionSelect').value || null;

        if (!category) {
            utils.showToast('Please select a category', 'warning');
            return;
        }

        if (isNaN(currentScore) || currentScore < 0 || currentScore > 100) {
            utils.showToast('Please enter a valid score (0-100)', 'warning');
            return;
        }

        utils.showLoading();
        this.currentCategory = category;

        try {
            const alternatives = await api.findAlternatives({
                product_category: category,
                current_score: currentScore,
                price_preference: pricePreference,
                region: region,
                limit: 10
            });

            this.displayAlternatives(alternatives);
            utils.showToast(`Found ${alternatives.length} alternatives`, 'success');
        } catch (error) {
            console.error('Search error:', error);
            utils.showToast('Search failed: ' + error.message, 'error');
        } finally {
            utils.hideLoading();
        }
    },

    displayAlternatives(alternatives) {
        const container = document.getElementById('alternativesList');
        const resultsDiv = document.getElementById('alternativesResults');

        if (alternatives.length === 0) {
            container.innerHTML = '<p class="text-muted">No alternatives found</p>';
            resultsDiv.style.display = 'block';
            return;
        }

        container.innerHTML = alternatives.map(alt => `
            <div class="product-card">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h5>${alt.name}</h5>
                        ${alt.brand ? `<p class="text-muted mb-1">${alt.brand}</p>` : ''}
                        <p class="mb-2">${utils.truncateText(alt.description || '', 150)}</p>
                        <div class="mb-2">
                            <span class="badge ${utils.getScoreBadgeClass(alt.hormonal_health_score)} badge-score">
                                Score: ${alt.hormonal_health_score.toFixed(1)}
                            </span>
                            ${alt.price_range ? `<span class="badge bg-secondary ms-2">${utils.formatPriceRange(alt.price_range)}</span>` : ''}
                        </div>
                        ${alt.free_from && alt.free_from.length > 0 ? `
                            <div class="mb-2">
                                <strong>Free from:</strong> ${alt.free_from.join(', ')}
                            </div>
                        ` : ''}
                        <small class="text-muted">${alt.match_reason}</small>
                    </div>
                    <button class="btn btn-sm btn-primary ms-3" onclick="AlternativesComponent.addToCart('${alt.product_id}', '${alt.name.replace(/'/g, "\\'")}')">
                        <i class="fas fa-plus"></i> Add
                    </button>
                </div>
            </div>
        `).join('');

        resultsDiv.style.display = 'block';
        resultsDiv.scrollIntoView({ behavior: 'smooth' });
    },

    async addToCart(productId, productName) {
        utils.showLoading();

        try {
            await api.addToShoppingList({
                user_id: APP_CONFIG.USER_ID,
                product_id: productId,
                device_id: APP_CONFIG.DEVICE_ID,
                replaced_product_category: this.currentCategory
            });

            utils.showToast(`${productName} added to shopping list`, 'success');
            await this.loadShoppingList();
        } catch (error) {
            console.error('Add to cart error:', error);
            utils.showToast('Failed to add to shopping list', 'error');
        } finally {
            utils.hideLoading();
        }
    },

    async loadShoppingList() {
        try {
            this.shoppingList = await api.getShoppingList(APP_CONFIG.USER_ID);
            this.displayShoppingList();
        } catch (error) {
            console.error('Load shopping list error:', error);
        }
    },

    displayShoppingList() {
        const container = document.getElementById('shoppingListContainer');
        const exportBtn = document.getElementById('exportListBtn');

        if (this.shoppingList.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">Your shopping list is empty</p>';
            exportBtn.style.display = 'none';
            return;
        }

        container.innerHTML = this.shoppingList.map(item => `
            <div class="shopping-list-item">
                <div>
                    <strong>${item.name}</strong>
                    <br>
                    <small class="text-muted">Score: ${item.hormonal_health_score.toFixed(1)}</small>
                </div>
                <button class="btn btn-sm btn-danger" onclick="AlternativesComponent.removeFromCart(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');

        exportBtn.style.display = 'block';
    },

    async removeFromCart(itemId) {
        utils.showLoading();

        try {
            await api.removeFromShoppingList(APP_CONFIG.USER_ID, itemId);
            utils.showToast('Item removed from shopping list', 'success');
            await this.loadShoppingList();
        } catch (error) {
            console.error('Remove from cart error:', error);
            utils.showToast('Failed to remove item', 'error');
        } finally {
            utils.hideLoading();
        }
    },

    exportShoppingList() {
        const text = this.shoppingList.map(item => 
            `${item.name} (Score: ${item.hormonal_health_score.toFixed(1)})`
        ).join('\n');

        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sakhi-shopping-list.txt';
        a.click();
        URL.revokeObjectURL(url);

        utils.showToast('Shopping list exported', 'success');
    }
};

window.AlternativesComponent = AlternativesComponent;
