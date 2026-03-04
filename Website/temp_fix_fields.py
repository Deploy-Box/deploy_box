import re

filepath = r"C:\Users\KBishop\code\deploy_box\Website\main_site\templates\accounts\signup.html"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add inline error <p> below each input in Step 1

# Username field - add error after the closing </div> of mt-1
content = content.replace(
    '''                        <label for="username" class="font-semibold text-sm text-zinc-300 pb-2 block">Username</label>
                        <div class="mt-1">
                            <input type="text" name="username" id="id_username" 
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter username" required />
                        </div>''',
    '''                        <label for="username" class="font-semibold text-sm text-zinc-300 pb-2 block">Username</label>
                        <div class="mt-1">
                            <input type="text" name="username" id="id_username" 
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter username" required />
                        </div>
                        <p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="username"></p>'''
)

# Email field (non-invite version)
content = content.replace(
    '''                            <input type="email" name="email" id="id_email"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter email address" required />
                            {% endif %}
                        </div>''',
    '''                            <input type="email" name="email" id="id_email"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter email address" required />
                            {% endif %}
                        </div>
                        <p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="email"></p>'''
)

# Password1 field
content = content.replace(
    '''                        <label for="password1" class="font-semibold text-sm text-zinc-300 pb-2 block">Password</label>
                        <div class="mt-1">
                            <input type="password" name="password1" id="id_password1"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Create password" required />
                        </div>''',
    '''                        <label for="password1" class="font-semibold text-sm text-zinc-300 pb-2 block">Password</label>
                        <div class="mt-1">
                            <input type="password" name="password1" id="id_password1"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Create password" required />
                        </div>
                        <p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="password1"></p>'''
)

# Password2 field
content = content.replace(
    '''                        <label for="password2" class="font-semibold text-sm text-zinc-300 pb-2 block">Confirm Password</label>
                        <div class="mt-1">
                             <input type="password" name="password2" id="id_password2"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Confirm password" required />
                        </div>''',
    '''                        <label for="password2" class="font-semibold text-sm text-zinc-300 pb-2 block">Confirm Password</label>
                        <div class="mt-1">
                             <input type="password" name="password2" id="id_password2"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Confirm password" required />
                        </div>
                        <p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="password2"></p>'''
)

# 2. Add inline errors to Step 2 fields

# First name
content = content.replace(
    '''                        <label for="first_name" class="font-semibold text-sm text-zinc-300 pb-2 block">First Name</label>
                        <div class="mt-1">
                             <input type="text" name="first_name" id="id_first_name"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter first name" required />
                        </div>''',
    '''                        <label for="first_name" class="font-semibold text-sm text-zinc-300 pb-2 block">First Name</label>
                        <div class="mt-1">
                             <input type="text" name="first_name" id="id_first_name"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter first name" required />
                        </div>
                        <p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="first_name"></p>'''
)

# Last name
content = content.replace(
    '''                        <label for="last_name" class="font-semibold text-sm text-zinc-300 pb-2 block">Last Name</label>
                        <div class="mt-1">
                             <input type="text" name="last_name" id="id_last_name"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter last name" required />
                        </div>''',
    '''                        <label for="last_name" class="font-semibold text-sm text-zinc-300 pb-2 block">Last Name</label>
                        <div class="mt-1">
                             <input type="text" name="last_name" id="id_last_name"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                placeholder="Enter last name" required />
                        </div>
                        <p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="last_name"></p>'''
)

# Birthdate
content = content.replace(
    '''                        <label for="birthdate" class="font-semibold text-sm text-zinc-300 pb-2 block">Birthdate</label>
                        <div class="mt-1">
                            <input type="date" name="birthdate" id="id_birthdate"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                required />
                        </div>''',
    '''                        <label for="birthdate" class="font-semibold text-sm text-zinc-300 pb-2 block">Birthdate</label>
                        <div class="mt-1">
                            <input type="date" name="birthdate" id="id_birthdate"
                                class="w-full px-4 py-3 bg-black/40 border border-zinc-700 text-white placeholder-zinc-500 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all duration-300"
                                required />
                        </div>
                        <p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="birthdate"></p>'''
)

print("Field error placeholders added successfully")
print(f"Total field-error elements: {content.count('field-error')}")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
