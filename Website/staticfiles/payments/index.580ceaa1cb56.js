// Get Stripe publishable key
fetch("/api/v1/payments/config")
  .then((result) => {
    return result.json();
  })
  .then((data) => {
    // Initialize Stripe.js
    const stripe = Stripe(data.public_key);

    // Event handler
    document.querySelectorAll("#submitBtn").forEach((button) => {
      button.addEventListener("click", () => {
        const stack_id = button.getAttribute("data-stack-id");
        const org_id = document.getElementById("org_dropdown").value;
        const project_id = document.getElementById("project_dropdown").value;

        // Validate selections
        if (!org_id) {
          alert("Please select an organization before purchasing");
          return;
        }
        if (!project_id) {
          alert("Please select a project before purchasing");
          return;
        }

        // Get Checkout Session ID
        fetch(`/api/v1/payments/checkout/create/${org_id}/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ stack_id: stack_id, project_id: project_id }),
        })
          .then((result) => {
            return result.json();
          })
          .then((data) => {
            console.log("sessionID", data);
            // Redirect to Stripe Checkout
            return stripe.redirectToCheckout({ sessionId: data.sessionId });
          })
          .then((res) => {
            console.log(res);
          });
      });
    });
  });

const org_dropdown = document.getElementById("org_dropdown");

org_dropdown.addEventListener("change", () => {
  const org_id = org_dropdown.value;
  console.log(org_id);

  let project_options = document.querySelectorAll("#project_dropdown option");

  project_options.forEach((option) => {
    console.log(option.getAttribute("org_id"));
    console.log(org_id);

    if (option.getAttribute("org_id") !== org_id) {
      option.style.display = "none";
    } else {
      option.style.display = "block";
    }
  });

  // Reset project dropdown to default placeholder when organization changes
  document.getElementById("project_dropdown").value = "";
});
