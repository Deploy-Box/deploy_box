document.addEventListener('DOMContentLoaded', function() {
    document
        .getElementById("addPaymentMethodBtn")
        .addEventListener("click", function () {
            document
                .getElementById("paymentForm")
                .classList.toggle("hidden");
        });

    // Fetch the publishable key from the server
    fetch("/api/v1/payments/config")
        .then((response) => response.json())
        .then((data) => {
            if (data.publicKey) {
                const stripe = Stripe(data.publicKey);
                const elements = stripe.elements();
                const cardElement = elements.create("card");
                cardElement.mount("#cardElement");

                const form = document.getElementById("stripePaymentForm");
                form.addEventListener("submit", async (event) => {
                    event.preventDefault();

                    const { error, paymentMethod } =
                        await stripe.createPaymentMethod({
                            type: "card",
                            card: cardElement,
                        });

                    if (error) {
                        document.getElementById("cardErrors").textContent =
                            error.message;
                    } else {
                        document.getElementById("cardErrors").textContent = "";

                        // Send paymentMethod.id to your server for further processing
                        fetch("/api/v1/payments/save-payment-method/", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                                payment_method_id: paymentMethod.id,
                                organization_id: document.getElementById("organizationId").value,
                            }),
                        })
                            .then((response) => response.json())
                            .then((result) => {
                                if (result.message) {
                                    alert(result.message);
                                    fetchCurrentCard(); // Refresh card information
                                } else if (result.error) {
                                    document.getElementById(
                                        "cardErrors"
                                    ).textContent = result.error;
                                }
                            })
                            .catch((error) => {
                                console.error(
                                    "Error saving payment method:",
                                    error
                                );
                            });
                    }
                });
            } else {
                console.error("Publishable key not found in response");
            }
        })
        .catch((error) => {
            console.error("Error fetching publishable key:", error);
        });

    // Add delete organization functionality
    document.getElementById('deleteOrgBtn').addEventListener('click', function() {
        if (confirm('Are you sure you want to delete this organization? This action cannot be undone.')) {
            const organizationId = document.getElementById('organizationId').value;
            fetch(`/api/v1/organizations/${organizationId}/`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                if (response.ok) {
                    window.location.href = '/organizations/'; // Redirect to organizations list
                } else {
                    throw new Error('Failed to delete organization');
                }
            })
            .catch(error => {
                console.error('Error deleting organization:', error);
                alert('Failed to delete organization. Please try again.');
            });
        }
    });

    // Function to fetch and display current card information
    function fetchCurrentCard() {
        const organizationId = document.getElementById('organizationId').value;
        fetch(`/api/v1/payments/payment-method/?organization_id=${organizationId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error fetching card:', data.error);
                    document.getElementById('currentCardInfo').classList.add('hidden');
                    return;
                }

                // Display card information
                document.getElementById('cardBrand').textContent = data.brand.charAt(0).toUpperCase() + data.brand.slice(1);
                document.getElementById('cardLast4').textContent = data.last4;
                document.getElementById('cardExpMonth').textContent = data.exp_month.toString().padStart(2, '0');
                document.getElementById('cardExpYear').textContent = data.exp_year.toString().slice(-2);
                document.getElementById('currentCardInfo').classList.remove('hidden');
            })
            .catch(error => {
                console.error('Error fetching card:', error);
                document.getElementById('currentCardInfo').classList.add('hidden');
            });
    }

    // Fetch current card information on page load
    fetchCurrentCard();

    // Add event listener for the remove card button
    document.getElementById('removeCardBtn').addEventListener('click', function() {
        if (confirm('Are you sure you want to remove this card?')) {
            const organizationId = document.getElementById('organizationId').value;
            fetch(`/api/v1/payments/payment-method/delete/?organization_id=${organizationId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (response.ok) {
                    document.getElementById('currentCardInfo').classList.add('hidden');
                } else {
                    if (data.error && data.error.includes('only payment method')) {
                        alert('You cannot remove your only payment method. Please add another payment method first.');
                    } else {
                        throw new Error(data.error || 'Failed to remove card');
                    }
                }
            })
            .catch(error => {
                console.error('Error removing card:', error);
                alert('Failed to remove card. Please try again.');
            });
        }
    });

    // Add plan cost reveal functionality
    const viewPlanBtn = document.getElementById('viewPlanBtn');
    let isCostRevealed = false;

    viewPlanBtn.addEventListener('click', function() {
        if (!isCostRevealed) {
            viewPlanBtn.textContent = '$10 / month';
            isCostRevealed = true;
        } else {
            viewPlanBtn.textContent = 'View Plan';
            isCostRevealed = false;
        }
    });
}); 