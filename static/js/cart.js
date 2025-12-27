// Sebet üçin JavaScript funksiýalary

// Sebedi localStorage-dan ýükle
let cart = JSON.parse(localStorage.getItem('cart') || '[]');

/**
 * Sebet sanyny täzelemek
 */
function updateCartDisplay() {
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    const countEl = document.getElementById('cart-count');
    
    if (countEl) {
        if (count > 0) {
            countEl.textContent = count;
            countEl.style.display = 'flex';
        } else {
            countEl.style.display = 'none';
        }
    }
}

/**
 * Sebede önüm goşmak
 */
function addToCart(id, name, price) {
    const existing = cart.find(item => item.id === id);
    
    if (existing) {
        existing.quantity++;
    } else {
        cart.push({ id, name, price, quantity: 1 });
    }
    
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartDisplay();
    alert(name + ' sebede goşuldy!');
}

/**
 * Sebet modalyny açmak
 */
function openCart() {
    const modal = document.getElementById('cartModal');
    const itemsDiv = document.getElementById('cart-items');
    
    if (!modal || !itemsDiv) return;
    
    if (cart.length === 0) {
        itemsDiv.innerHTML = '<p style="text-align: center; padding: 2rem;">Sebediňiz boş</p>';
        document.getElementById('cart-total').textContent = '0.00';
    } else {
        let html = '';
        let total = 0;
        
        cart.forEach((item, index) => {
            const subtotal = item.price * item.quantity;
            total += subtotal;
            
            html += `
                <div style="padding: 1rem; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${item.name}</strong><br>
                        <span style="color: #666;">$${item.price.toFixed(2)} × ${item.quantity} = $${subtotal.toFixed(2)}</span>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn btn-warning" onclick="updateQuantity(${index}, -1)" style="padding: 0.3rem 0.6rem;">−</button>
                        <button class="btn btn-warning" onclick="updateQuantity(${index}, 1)" style="padding: 0.3rem 0.6rem;">+</button>
                        <button class="btn btn-danger" onclick="removeFromCart(${index})" style="padding: 0.3rem 0.6rem;">×</button>
                    </div>
                </div>
            `;
        });
        
        itemsDiv.innerHTML = html;
        document.getElementById('cart-total').textContent = total.toFixed(2);
    }
    
    modal.style.display = 'block';
}

/**
 * Sebet modalyny ýapmak
 */
function closeCart() {
    const modal = document.getElementById('cartModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Önüm mukdaryny täzelemek
 */
function updateQuantity(index, change) {
    cart[index].quantity += change;
    
    if (cart[index].quantity <= 0) {
        cart.splice(index, 1);
    }
    
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartDisplay();
    openCart();
}

/**
 * Önümi sebetden aýyrmak
 */
function removeFromCart(index) {
    if (confirm('Bu önümi sebetden aýyrmak isleýärsiňizmi?')) {
        cart.splice(index, 1);
        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartDisplay();
        openCart();
    }
}

/**
 * Sargyt etmek
 */
function placeOrder() {
    const name = document.getElementById('customer-name').value.trim();
    const phone = document.getElementById('customer-phone').value.trim();
    
    if (!name || !phone) {
        alert('Adyňyzy we telefon belgiňizi giriziň');
        return;
    }
    
    if (cart.length === 0) {
        alert('Sebediňiz boş');
        return;
    }
    
    // Sargyt maglumatlaryny server-e ibermek
    fetch('/api/orders', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: name,
            phone: phone,
            items: cart
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Sargyt üstünlikli ýerleşdirildi!\nSargyt belgiňiz: ' + data.order_id);
            
            // Sebedi arassalamak
            cart = [];
            localStorage.setItem('cart', JSON.stringify(cart));
            updateCartDisplay();
            closeCart();
            
            // Sargyt yzarlamak sahypasyna geçmek
            window.location.href = '/track-order?id=' + data.order_id;
        } else {
            alert('Ýalňyşlyk ýüze çykdy: ' + (data.message || 'Nämedir bir ýalňyşlyk'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Sargyt ýerleşdirilende ýalňyşlyk ýüze çykdy');
    });
}

/**
 * Modal daşynda basmak bilen ýapmak
 */
window.onclick = function(event) {
    const modal = document.getElementById('cartModal');
    if (event.target == modal) {
        closeCart();
    }
}

// Sahypa ýüklenensoň sebet sanyny täzelemek
document.addEventListener('DOMContentLoaded', function() {
    updateCartDisplay();
});