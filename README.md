# Introduction
This is the backend for the marketplace for battery recycling.

# Getting Started
0. If working on cloud:
    ssh -i .\connectsu-re-yti_key.pem azureuser@20.244.10.110

1. Clone the repo

    git clone https://dev.azure.com/tc-pvt-ltd/Yokogawa%20-%20GreenBooster%20PoC/_git/marketplace-be
    git clone https://dev.azure.com/tc-pvt-ltd/Yokogawa%20-%20GreenBooster%20PoC/_git/marketplace-fe

2. Install dependencies:

    # Node.js
    sudo apt update
    sudo apt install nodejs npm

    # Python
    # uv is package manager. This has to be available globally.
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # either restart the shell or source the env file
    source $HOME/.local/bin/env
    # Update python, and setup venv
    cd marketplace-be
    uv sync
    # Setup node-env
    cd marketplace-fe
    npm i

## Setup marketplace-fe/.env:

    VITE_API_BASE_URL=http://20.244.10.110:8000
    VITE_API_WEB_SOCKET_BASE_URL=ws://20.244.10.110:8000

## Setup marketplace-be/.env.common:

# The file must have the following fields:

    DOMAIN="localhost"
    CORS_ALLOW_UI_URL="http://localhost:5713"
    SECRET_KEY=""
    ALGORITHM="HS256"
    OPENAI_API_TOKEN=""
    ENDPOINT=""
    OPENAI_API_VERSION=""
    DEPLOYMENT="gpt-4o-mini"
    NAMESPACE_CONNECTION_STR=""


# Run backend
    
    cd marketplace-be

    # Setup dbs and entities
    uv run -m src.setup

    # Run main app
    uv run uvicorn src.main:app --host 0.0.0.0 --env-file .env.marketplace

    # Run agent app
    uv run uvicorn src.agent:app --port 8001 --env-file .env.manufacturer
    uv run uvicorn src.agent:app --port 8002 --env-file .env.recycler
    uv run uvicorn src.agent:app --port 8003 --env-file .env.recycler_2
    uv run uvicorn src.agent:app --port 8004 --env-file .env.fleet
    uv run uvicorn src.agent:app --port 8005 --env-file .env.manufacturer_2
    uv run uvicorn src.agent:app --port 8009 --env-file .env.market_agent

    uv run -m src.tests.2_create_listing
    uv run -m src.tests.3_auction_flow
    uv run -m src.tests.4_negotiation_flow
    uv run -m src.tests.5_contact_buyer_flow
    uv run -m src.tests.6_reject_negotiation
    uv run -m src.tests.7_buy_it_now_flow
    uv run -m src.tests.10_back_office_api
    uv run -m src.tests.11_create_listing_scenario

# Utils:

Use this to find the PID of process running on a port:

    lsof -ti:8000

Use this to view all processes running from the marketplace:

    ss -ltnp | grep 800

Use this to kill the process:

    kill $(lsof -ti:8000)

Use this in case you get a parsing error for windows style characters in the script.
You might get this when using WSL.

    sed -i 's/\r$//' ./runner.sh 
    sed -i 's/\r$//' ./shutdown.sh 

# Run frontend:

    cd marketplace-fe
    npm run build
    sudo rm -rf /var/www/html/dist
    sudo cp -R dist /var/www/html/
    sudo systemctl restart nginx

# Building Docker Images:

Highly recommend using lazydocker:

    choco install lazydocker

To run:

    uv run -m src.build
    cp -r ..\marketplace-fe\dist\ .\dist\frontend\
    docker compose build
    lazydocker

The rest of these commands can be used when needed.

    docker build -t base-image -f dist/base_image/Dockerfile .
    docker build -t marketplace-image -f dist/marketplace/Dockerfile .
    docker build -t manufacturer-image -f dist/manufacturer/Dockerfile .
    docker build -t manufacturer_2-image -f dist/manufacturer_2/Dockerfile .
    docker build -t recycler-image -f dist/recycler/Dockerfile .
    docker build -t recycler_2-image -f dist/recycler_2/Dockerfile .
    docker build -t fleet-image -f dist/fleet/Dockerfile .
    docker build -t oem-image -f dist/oem/Dockerfile .
    docker build -t frontend-image -f dist/frontend/Dockerfile .


    docker run --env-file .env --env-file .\.env.marketplace -p 8000:8000 marketplace-image
    docker run --env-file .env --env-file .\.env.manufacturer -p 8001:8001 manufacturer-image

    docker save -o base-image.tar base-image:latest
    docker save -o marketplace-image.tar marketplace-image:latest
    docker save -o manufacturer-image.tar manufacturer-image:latest
    docker save -o manufacturer_2-image.tar manufacturer_2-image:latest
    docker save -o recycler-image.tar recycler-image:latest
    docker save -o recycler_2-image.tar recycler_2-image:latest
    docker save -o fleet-image.tar fleet-image:latest
    docker save -o oem-image.tar oem-image:latest
    

# Service bus usage design:

One queue for holding all messages.
There will N topics in this queue, one for each user.
There will be two subscribers for each topic, which will be created when we register a new user.

One subscriber is for the human: with this, we will push notifications to the front end.
One subscriber is for the agent: the agent will get messages, and respond on behalf of the human, if
   the human has given permission. If the bot should not get certain messages, we can use filters.

All agents will be allowed to send messages to each other. The receiving user's id has to be known, and the topic name of the dst will be topic_{dst_user_id}.

## Questions:
1. Once a message is consumed by a subscriber, can the same subscriber go back and read older messages?

   We can't replay with servicebus. 
   We have to store the messages in the database. 
   We will get the older messages from the db for GET /inbox.
   In essence, we will need servicebus for pushing notifications. Servicebus cannot act as a log (unlike redis).

2. Suppose a topic has some messages, and then a new subscriber is created. Can the subscriber listen to
   the existing messages (from first) or does it get newer messages only?

   We have to create the subscriber on user registration... If we add the agent-subscriber later, then it will only get the upcoming / newer messages.

# Todo:

1. Go back to tick model, with demands and supplies coming in a different times.
	Each buyer responds to the seller.
	Seller accepts offers from one buyer.
2. Simulation through back-office. 
3. APIs for back-office. 
4. Agents - plan
5. Testing with prompts and LLMs.
 
All agents will have P throughput.
All agents will have Q stock.
All agents will have R price.

Day  0: Demand B tons from Manufacturer, to be satisfied in 21 days.
Day  1:|---> Gets N offers from N Recycler, each with enough capacity to satisfy this listing.
Day  1:|---> One recycler X wins, has to satisfy in 21 days.
             - Only one recycler X will quote a low price. 
             - The rest of them will quote higher prices.
             - That recycler X has enough doesn't have enough stock.
             - That recycler X will procure battery waste, to make raw materials.
Day  1:|---> X places a new demand for battery waste, to be satisfied in 10 days.
Day  2:|---> X gets M offers from M ev-fleets
Day  2:|---> One ev-fleet Y wins
Day  9:|---> Y supplies battery waste to X
Day 15:|---> X supplies raw material to manufacturer.
 
We are missing the concept of threads in listings... Will add this column to listing table.
When a recycler is creating a demand to satisfy another listing, they should 
reuse the incoming thread id. This will help us track the transactions between
multiple entities.

The listing.thread_id is a public variable (at least in the agentic layer, thread id can be hidden in the UI). 
All actions on this listing, will be viewable through this thread_id, in the back-office app.

# Assets.db design

## For most industries,
### constants:
    maximum_production_capacity
    profit_percentage
    initial_stock (material_code, quantity, unit)
    initial_demand (material_code, quantity, unit)
    procurement_budget (material_code, unit_cost_price)
    processing_cost (material_code, unit_cost_price)

### daily_variables:
    procured_material (type, quantity, unit)
    yield (type, quantity, unit)
    
### derived_variables

    current_stock = (stock[day-1] if day > 0 else initial_stock) - quantity_produced + quantity_procured
    # unit cost price comes from seller
    # procured_quantity depends on demand and initial_stock
    procurement_cost = unit_cost_price * procured_quantity
    # unit_logistics_price comes from logistics provider
    logistics_costs = unit_logistics_price * procured_quantity
    processing_costs = unit_processing_price * quantity_produced
    selling_price = (procurement_cost + logistics_costs + processing_costs) * (1 + (profit / 100))

## Ev_fleet,
### Constants:
* EOL threshold cycles (per battery type)

### Independent variables:
* Battery capacity (MWh)
* batteries_count
* battery_cycles

## Manufacturer
* raw_materials_required: dict[material_code, quantity] to hit some target_battery_efficiency

## Recycler

### Constants:
* recovery_rate (per material type)
### Derived
* yield = processed_quantity * recovery_rate

## Logistics
* maintain a first-come first-serve scheme: reserve trucks, and make a quote saying you will
    deliver X amount of Y material in Z days.
* logistics agent must send a delivered message via the marketplace
* only logistics is concerned with time, all other agents work on their tasks in the span of a day.
* Logistics has to inform how much shipping will cost.
* After supplier calls logistics agent, the logistics agent can notify the receiver that 
    their package has been delivered. We really don't have to wait for time to pass.
    It's like calling for an auto. You don't call auto for some day in the future, it can be hired on demand.
    
## Constants
* Shipping cost per km per kg

## Independents:
* number of trucks
* truck capacity

## Data structure
* Truck availability

----------
# Back-office 

0. GET /scenario-types

1. get /scenario
    [{
        "scenario_name": "",
        "desc":"",
        "tag": "enum",
        "expected_outcome":"",
        # you'll know the following fields after simulation has run once
        "outputs": {
            "number_of_agents":len(participants),
            "participants":[],         
            "duration": "",
            "number_of_steps": int
        }
    }]

2. post /scenario/start
    request: {
        "scenario_id": ""
    }
    response: {
        "run_id": "",
    }

3. ws://scenario/event/{run_id}
    yield: {
        "event_type": MessageType
        "payload":{
            "title": "agent name",
            "description": "new listing | place bid | new highest bid",
            "rationale": "reasoning generated by LLM",
            "variables": {},
            "last_message":""
        }
    }

4. get /scenario/transaction?run_id=[run_id]|scenario_id
    If no run_id in query_params, fetch latest run for that scenario and user.
    [{
        ... parent_listings_object | { events: [] }
    }]


There is a scenario.
When you run a scenario, a new Run object (and run_id) is created.
Run object can look like this:
    {
        "run_id": ""
    }

Inside this run, there will be multiple threads, threads look like this:
    A1 -> B1 -> C1
    A2 -> B2 -> C2

Each thread can be extracted with this algorithm:
    1. Fetch all messages under this run_id
    

B1 is a listing, created in response to A1.
B2 is a listing, created in response to A2.


When you hit, get /scenario/transaction?run_id=[run_id]|scenario_id
I have to get A1 and A2, which will be cards in the Scenario Threads page.

The events which show up when you click on A1 or A2.

5. GET /agents
Forward [fetch("x/card-details") for x in alive_users]

response: [x.agents for x in User.select()]
    {
        "agent-name": "",
        "capabilities": "",
    }


## TODO:

Agents on start-up must:
* fetch /openapi.json
* login
* send card-details

1. Drivers
2. Time taken to run
3. Bugs / 400 / 500 errors
4. Running all drivers in a sequence
5. Marketplace.db data
6. Even without agents, for normal users, the marketplace should work.
With some premium users, you will be adding agents.
7. Simulation configs: constants, independents, dependents, targets.
    Get these for all the user types one by one.
    Develop the DSL usage first. Then you'll know exactly which features are needed.


A -> B

A -> Y -> B -> C -> D -> E 

You have to find out which numbers must be quoted.

A - cost price - 80
A - selling price - 100

Y - cost price - 100
Y - sell price - 120

B - cost price - 120


{
    "listing_id": "",
    "children": [
        {
            "listing_id":"",
            "children":[]
        }
    ]
}

If the request doesn't have a run id, create a new one.

If the listing has been created in response to another listing, then the parent_listing_id can be specified in the payload.



max production capacity
initial Stock
initial demand
demand-supply material mapping
procurement budget
max yield per procured battery
unit production cost

1. Check maximum production capacity
2. Enter negotiation | auction
3. If offer accepted, 
    | check inventory for finished goods
    | check inventory for raw materials
4. Post demand listing for raw materials if required


battery efficiency
soh
battery chemistry | battery type produced

# End-to-end scenario

Manufacturer - M
Recycler - R
Ev-fleet - F

1. M observes an accepted order in its asset db.
2. M checks stock for raw materials required for the order.
3. M places an order for shortages. This order must include
    material_code | quantity | units | quality | time | location | budget
    material code, quantity, units will be known from demand_supply_mapping.
    quality is a constant string.
    time depends on the order delivery date.
    location is user location.
    budget ?
4. M marks the order as procuring. 
5. R receives service bus message market_listing_announcement.
6. R checks message type, listing type, material_code
7. R checks production schedule (?), production capacity, to decide if it will make an offer.
8. R acknowledges the invite, makes an entry in its Orders table, with listing id as the invite message listing id
    and status acknowledged.
9. R makes an offer, at X markup of cost price. 
10. R gets accepted. R marks the order as accepted.
11. R checks stock for waste batteries required for the order.
12. R places an order for shortages. This order must include
   material_code | quantity | units | quality | time | location | budget
   material code, quantity, units will be known from demand_supply_mapping.
   quality is a constant string.
   time depends on the order delivery date.
   location is user location.
   budget ?
13. R marks the order as processing.
14. F receives service bus message market_listing_announcement.
15. F checks message type, listing type, material_code
16. F checks production schedule (?), production capacity, to decide if it will make an offer.
17. F acknowledges the invite, makes an entry in its Orders table, with listing id as the invite message listing id
   and status acknowledged.
18. F makes an offer, at X markup of cost price.
19. F gets accepted. F marks the order as accepted. 
20. F checks stock for waste batteries required for the order.
21. F has sufficient stock. F calls logistics.
22. Logistics delivers to R.
23. R marks its calendar (once all the children listings are delivered) and starts production.
24. R starts producing the materials, and informs logistics once it is done.
25. Logistics delivers to M. M marks its calendar and starts production.
26. M starts producing materials, and completes its orders.

# Reasoning

There are three kinds of strings to be generated:
1. Message: Direct, Active voice: the message sent from one agent to another, for example:
   "I offer this, I'm willing to cover logistics also"
   "I'm rejecting your offer, I can't accept any new requests from you."
   "Your offer was way too low, I need more"
   "Your bid is way too high. I accepted it and closed the auction."
2. Description: Passive voice: the action taken by the agent.
   "New highest bid received."
   "New active order found. Procuring raw materials for this order."
3. Chain-of-thought:
   (scenario) + (input variables [service bus message]) + (decision taken [output from message handler])