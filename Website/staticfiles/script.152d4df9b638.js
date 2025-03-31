console.log("Sanity Check")

document.addEventListener("DOMContentLoaded", function () {
  // Use the containersUrl variable defined in the template
  fetch(containersUrl)
    .then((response) => response.json())
    .then((data) => {
      const containerWrapper = document.getElementById("container-wrapper");
      data.forEach((container) => {
        const containerDiv = document.createElement("div");
        containerDiv.classList.add(
          "p-10",
          "rounded-l-xl",
          "border",
          "border-blue-gray-100",
          "rounded-xl",
          "bg-no-repeat",
          "lg:bg-contain",
          "bg-cover",
          "bg-right",
          "mb-5",
          "w-2/3"
        );

        containerDiv.innerHTML = `
            <p class="block antialiased font-sans text-sm font-light leading-normal text-blue-gray-900 font-bold mb-2">
              ${container.feature}
            </p>
            <h3 class="block antialiased tracking-normal font-sans text-3xl font-semibold leading-snug text-blue-gray-900">
              ${container.title}
            </h3>
            <p class="block antialiased font-sans text-base font-light leading-relaxed text-inherit mt-2 mb-6 !text-base font-normal text-gray-500">
              ${container.description}
            </p>
            <button class="align-middle select-none font-sans font-bold text-center uppercase transition-all disabled:opacity-50 disabled:shadow-none disabled:pointer-events-none text-xs py-3 px-6 rounded-lg border border-gray-900 text-gray-900 hover:opacity-75 focus:ring focus:ring-gray-300 active:opacity-[0.85] flex-shrink-0" type="button" data-ripple-dark="true">
              ${container.button1Text}
            </button>
            <button class="align-middle select-none font-sans font-bold text-center uppercase transition-all disabled:opacity-50 disabled:shadow-none disabled:pointer-events-none text-xs py-3 px-6 rounded-lg border border-gray-900 text-gray-900 hover:opacity-75 focus:ring focus:ring-gray-300 active:opacity-[0.85] flex-shrink-0" type="button" data-ripple-dark="true">
              ${container.button2Text}
            </button>
          `;

        containerWrapper.appendChild(containerDiv);
      });
    })
    .catch((error) => console.error("Error loading containers:", error));
});

function getUserDetails() {
  fetch("/accounts/me")
    .then((response) => response.json())
    .then((data) => {
      if (data.username) {
        document.getElementById("username").value = data.username;
      }
      if (data.email) {
        document.getElementById("email").value = data.email;
      }
    })
    .catch((error) =>
      console.error("Error fetching user details:", error)
    );
}

// Auto-fill user details when the page loads
window.onload = getUserDetails;

document
  .getElementById("resetPassword")
  .addEventListener("click", function () {
    const email = document.getElementById("resetEmail").value;

    if (!email) {
      alert("Please enter your email.");
      return;
    }

    fetch("accounts/password-reset/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email }),
    })
      .then((response) => response.json())
      .then((data) => {
        alert(data.message || "Check your email for the reset link.");
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred. Please try again.");
      });
  });

document
  .getElementById("userForm")
  .addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent default form submission

    const username = document.getElementById("username").value;
    const email = document.getElementById("email").value;

    fetch("/accounts/update-user/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username, email: email }),
      credentials: "include",
    })
      .then((response) => response.json())
      .then((data) => {
        alert(data.message || data.error);
      })
      .catch((error) => console.error("Error updating user:", error));
  });