"""
Default node templates seeded into the database on first startup.
Matches the frontend nodeTypes catalogue exactly.
"""

NODE_TEMPLATES = [
    # ── Triggers ──────────────────────────────────
    {"id": "manual-trigger",  "name": "Manual Trigger",    "icon": "⚡",  "color": "from-yellow-400 via-orange-400 to-red-500",     "category": "Triggers",         "description": "Start a workflow manually with a single click"},
    {"id": "schedule",        "name": "Schedule",           "icon": "⏰",  "color": "from-blue-400 via-indigo-400 to-purple-500",    "category": "Triggers",         "description": "Run workflows on a cron schedule"},
    {"id": "webhook",         "name": "Webhook",            "icon": "🔗",  "color": "from-cyan-400 via-teal-400 to-green-500",       "category": "Triggers",         "description": "Trigger workflows via an incoming HTTP request"},
    {"id": "email-trigger",   "name": "Email Trigger",      "icon": "📨",  "color": "from-pink-400 via-rose-400 to-red-500",         "category": "Triggers",         "description": "Trigger when a new email arrives"},

    # ── AI & ML ───────────────────────────────────
    {"id": "openai",          "name": "OpenAI (ChatGPT)",  "icon": "🧠",  "color": "from-emerald-400 via-teal-400 to-cyan-500",     "category": "AI & ML",          "description": "Generate text, chat, and images with OpenAI GPT & DALL-E models"},
    {"id": "anthropic",       "name": "Anthropic Claude",   "icon": "🤖",  "color": "from-orange-400 via-amber-400 to-yellow-500",   "category": "AI & ML",          "description": "Generate text with Claude models"},
    {"id": "huggingface",     "name": "HuggingFace",        "icon": "🤗",  "color": "from-yellow-400 via-orange-400 to-amber-500",   "category": "AI & ML",          "description": "Run inference on HuggingFace models"},
    {"id": "gemini",          "name": "Google Gemini",      "icon": "✨",  "color": "from-blue-400 via-purple-400 to-pink-500",      "category": "AI & ML",          "description": "Generate content and chat with Google Gemini AI models"},
    {"id": "ai-agent",        "name": "AI Agent",           "icon": "👾",  "color": "from-purple-400 via-fuchsia-400 to-pink-500",   "category": "AI & ML",          "description": "Autonomous AI agent with tool use"},
    {"id": "text-analysis",   "name": "Text Analysis",      "icon": "📝",  "color": "from-blue-400 via-cyan-400 to-teal-500",        "category": "AI & ML",          "description": "Sentiment, classification, NER and more"},
    {"id": "image-gen",       "name": "Image Generation",   "icon": "🎨",  "color": "from-pink-400 via-purple-400 to-indigo-500",    "category": "AI & ML",          "description": "Generate images from text prompts"},

    # ── Communication ─────────────────────────────
    {"id": "slack",           "name": "Slack",              "icon": "💬",  "color": "from-purple-400 via-pink-400 to-rose-500",      "category": "Communication",    "description": "Send messages and manage Slack channels"},
    {"id": "discord",         "name": "Discord",            "icon": "🎮",  "color": "from-indigo-400 via-purple-400 to-pink-500",    "category": "Communication",    "description": "Send messages to Discord servers"},
    {"id": "teams",           "name": "Microsoft Teams",    "icon": "👥",  "color": "from-blue-400 via-indigo-400 to-purple-500",    "category": "Communication",    "description": "Post to Teams channels and chats"},
    {"id": "telegram",        "name": "Telegram",           "icon": "✈️",  "color": "from-cyan-400 via-blue-400 to-indigo-500",      "category": "Communication",    "description": "Send Telegram messages and manage bots"},
    {"id": "email",           "name": "Email",              "icon": "📧",  "color": "from-red-400 via-pink-400 to-rose-500",         "category": "Communication",    "description": "Send emails via SMTP or API"},
    {"id": "sms",             "name": "SMS",                "icon": "💌",  "color": "from-green-400 via-emerald-400 to-teal-500",    "category": "Communication",    "description": "Send SMS via Twilio or similar"},

    # ── Data & Storage ────────────────────────────
    {"id": "postgresql",      "name": "PostgreSQL",         "icon": "🐘",  "color": "from-blue-500 via-indigo-500 to-blue-600",      "category": "Data & Storage",   "description": "Query and manage PostgreSQL databases"},
    {"id": "mongodb",         "name": "MongoDB",            "icon": "🍃",  "color": "from-green-500 via-emerald-500 to-teal-600",    "category": "Data & Storage",   "description": "Query and manage MongoDB collections"},
    {"id": "redis",           "name": "Redis",              "icon": "⚡",  "color": "from-red-500 via-orange-500 to-amber-600",      "category": "Data & Storage",   "description": "Read and write Redis keys"},
    {"id": "mysql",           "name": "MySQL",              "icon": "🐬",  "color": "from-blue-400 via-cyan-400 to-teal-500",        "category": "Data & Storage",   "description": "Query and manage MySQL databases"},
    {"id": "google-sheets",   "name": "Google Sheets",      "icon": "📊",  "color": "from-green-400 via-emerald-400 to-green-500",   "category": "Data & Storage",   "description": "Read and write Google Sheets data"},
    {"id": "airtable",        "name": "Airtable",           "icon": "📋",  "color": "from-yellow-400 via-orange-400 to-red-500",     "category": "Data & Storage",   "description": "Manage Airtable bases and records"},
    {"id": "csv",             "name": "CSV",                "icon": "📄",  "color": "from-slate-400 via-gray-400 to-zinc-500",       "category": "Data & Storage",   "description": "Parse and generate CSV files"},

    # ── Logic & Flow ──────────────────────────────
    {"id": "if-condition",    "name": "IF Condition",       "icon": "🔀",  "color": "from-amber-400 via-orange-400 to-red-500",      "category": "Logic & Flow",     "description": "Branch the workflow based on conditions"},
    {"id": "switch",          "name": "Switch",             "icon": "🔄",  "color": "from-purple-400 via-violet-400 to-indigo-500",  "category": "Logic & Flow",     "description": "Route to different branches based on value"},
    {"id": "loop",            "name": "Loop",               "icon": "🔁",  "color": "from-cyan-400 via-blue-400 to-indigo-500",      "category": "Logic & Flow",     "description": "Iterate over a list of items"},
    {"id": "merge",           "name": "Merge",              "icon": "🔗",  "color": "from-green-400 via-teal-400 to-cyan-500",       "category": "Logic & Flow",     "description": "Merge multiple branches into one"},
    {"id": "split",           "name": "Split",              "icon": "✂️",  "color": "from-pink-400 via-rose-400 to-red-500",         "category": "Logic & Flow",     "description": "Split data into multiple branches"},
    {"id": "wait",            "name": "Wait",               "icon": "⏸️",  "color": "from-blue-400 via-indigo-400 to-purple-500",    "category": "Logic & Flow",     "description": "Pause workflow execution for a duration"},

    # ── Data Processing ───────────────────────────
    {"id": "transform",       "name": "Transform Data",     "icon": "⚙️",  "color": "from-teal-400 via-cyan-400 to-blue-500",        "category": "Data Processing",  "description": "Map, rename, and reshape data fields"},
    {"id": "filter",          "name": "Filter",             "icon": "🔍",  "color": "from-indigo-400 via-purple-400 to-pink-500",    "category": "Data Processing",  "description": "Filter items based on conditions"},
    {"id": "aggregate",       "name": "Aggregate",          "icon": "📊",  "color": "from-orange-400 via-amber-400 to-yellow-500",   "category": "Data Processing",  "description": "Aggregate data with sum, avg, count, etc."},
    {"id": "sort",            "name": "Sort",               "icon": "↕️",  "color": "from-green-400 via-emerald-400 to-teal-500",    "category": "Data Processing",  "description": "Sort items by a field"},
    {"id": "json",            "name": "JSON",               "icon": "{ }",  "color": "from-yellow-400 via-amber-400 to-orange-500",  "category": "Data Processing",  "description": "Parse and stringify JSON data"},

    # ── APIs & Services ───────────────────────────
    {"id": "http",            "name": "HTTP Request",       "icon": "🌐",  "color": "from-green-400 via-emerald-400 to-teal-500",    "category": "APIs & Services",  "description": "Make HTTP requests to any URL"},
    {"id": "rest-api",        "name": "REST API",           "icon": "🔌",  "color": "from-blue-400 via-cyan-400 to-teal-500",        "category": "APIs & Services",  "description": "Interact with RESTful APIs"},
    {"id": "graphql",         "name": "GraphQL",            "icon": "◆",   "color": "from-pink-400 via-fuchsia-400 to-purple-500",   "category": "APIs & Services",  "description": "Execute GraphQL queries and mutations"},
    {"id": "stripe",          "name": "Stripe",             "icon": "💳",  "color": "from-indigo-400 via-purple-400 to-violet-500",  "category": "APIs & Services",  "description": "Manage payments and subscriptions"},
    {"id": "github",          "name": "GitHub",             "icon": "🐙",  "color": "from-slate-500 via-gray-500 to-zinc-600",       "category": "APIs & Services",  "description": "Manage repos, issues, and pull requests"},
    {"id": "aws",             "name": "AWS",                "icon": "☁️",  "color": "from-orange-400 via-amber-400 to-yellow-500",   "category": "APIs & Services",  "description": "Interact with AWS services (S3, Lambda, etc.)"},

    # ── Analytics ─────────────────────────────────
    {"id": "google-analytics","name": "Google Analytics",   "icon": "📈",  "color": "from-orange-400 via-red-400 to-pink-500",       "category": "Analytics",        "description": "Read Google Analytics data"},
    {"id": "mixpanel",        "name": "Mixpanel",           "icon": "📊",  "color": "from-purple-400 via-fuchsia-400 to-pink-500",   "category": "Analytics",        "description": "Send events and query Mixpanel data"},
    {"id": "segment",         "name": "Segment",            "icon": "🎯",  "color": "from-green-400 via-emerald-400 to-teal-500",    "category": "Analytics",        "description": "Track events and manage user data"},

    # ── Google Workspace ────────────────────────────────
    {"id": "google-docs",     "name": "Google Docs",        "icon": "📄",  "color": "from-blue-400 via-indigo-400 to-blue-600",     "category": "Google Workspace", "description": "Create, read, update, delete, and search Google Docs"},
    {"id": "google-drive",    "name": "Google Drive",       "icon": "📁",  "color": "from-yellow-400 via-green-400 to-blue-500",    "category": "Google Workspace", "description": "List, upload, download, delete, and share files on Google Drive"},
    {"id": "gmail",           "name": "Gmail",              "icon": "✉️",  "color": "from-red-400 via-red-500 to-rose-600",         "category": "Google Workspace", "description": "Send, read, search, and manage Gmail messages"},
    {"id": "google-sheets",   "name": "Google Sheets",      "icon": "📊",  "color": "from-green-400 via-emerald-400 to-green-600",  "category": "Google Workspace", "description": "Create, read, write, and append data in Google Sheets","default_data": {}},
    {"id": "google-forms",    "name": "Google Forms",       "icon": "📋",  "color": "from-purple-400 via-violet-400 to-purple-600", "category": "Google Workspace", "description": "Create forms, add questions, and collect responses"},
]
