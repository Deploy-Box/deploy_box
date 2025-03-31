const currentPath = window.location.pathname;

const navbar = document.getElementById('navbar');
const navbarText = document.getElementById('navbar-text');
const home = document.getElementById('home')
const stacks = document.getElementById('stacks');
const pricing = document.getElementById('pricing');
const contact = document.getElementById('contact');
const login = document.getElementById('login')

// Listen for scroll events
if (currentPath == '/'){
    window.addEventListener('scroll', () => {
        if (window.scrollY > 500) {
        // When scrolling past 50px, change navbar background and text color
        navbar.classList.add('bg-white', 'text-black');
        navbarText.classList.add('text-black');
        stacks.classList.add('text-black'); // Change text color to black
        pricing.classList.add('text-black'); // Change text color to black
        login.classList.add('text-black');
        login.classList.add('border-black');
        contact.classList.add('text-black'); // Change text color to black
        navbar.classList.remove('bg-transparent', 'text-white');
        navbarText.classList.remove('text-white')
        stacks.classList.remove('text-white'); // Ensure text color is removed
        pricing.classList.remove('text-white'); // Ensure text color is removed
        contact.classList.remove('text-white'); // Ensure text color is removed
        login.classList.remove('text-white');
        login.classList.remove('border-white');
        } else {
        // When at the top, revert to original transparent background and white text
        navbar.classList.remove('bg-white', 'text-black');
        navbar.classList.add('bg-transparent', 'text-white');
        navbarText.classList.remove('text-black');
        navbarText.classList.add('text-white'); // Revert text color to white
        stacks.classList.remove('text-black');
        stacks.classList.add('text-white'); // Revert text color to white
        pricing.classList.remove('text-black');
        pricing.classList.add('text-white'); // Revert text color to white
        contact.classList.remove('text-black');
        contact.classList.add('text-white'); // Revert text color to white
        login.classList.remove('text-black');
        login.classList.add('text-white');
        login.classList.remove('border-black');
        login.classList.add('border-white');
        }
    });

}

if (currentPath == '/stacks'){

    stacks.classList.remove('text-white');
    stacks.classList.add('text-emerald-400');
    home.classList.add('text-white')
    home.classList.remove('text-emerald-400');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 500) {
        // When scrolling past 50px, change navbar background and text color
        navbar.classList.add('bg-white', 'text-black');
        navbarText.classList.add('text-black');
        home.classList.add('text-black')
        home.classList.remove('text-white')
        pricing.classList.add('text-black'); // Change text color to black
        login.classList.add('text-black');
        login.classList.add('border-black');
        contact.classList.add('text-black'); // Change text color to black
        navbar.classList.remove('bg-transparent', 'text-white');
        navbarText.classList.remove('text-white')
        pricing.classList.remove('text-white'); // Ensure text color is removed
        contact.classList.remove('text-white'); // Ensure text color is removed
        login.classList.remove('text-white');
        login.classList.remove('border-white');
        } else {
        // When at the top, revert to original transparent background and white text
        navbar.classList.remove('bg-white', 'text-black');
        navbar.classList.add('bg-transparent', 'text-white');
        navbarText.classList.remove('text-black');
        navbarText.classList.add('text-white'); // Revert text color to white
        home.classList.add('text-white');
        home.classList.remove('text-black');
        pricing.classList.remove('text-black');
        pricing.classList.add('text-white'); // Revert text color to white
        contact.classList.remove('text-black');
        contact.classList.add('text-white'); // Revert text color to white
        login.classList.remove('text-black');
        login.classList.add('text-white');
        login.classList.remove('border-black');
        login.classList.add('border-white');
        }
    });

}