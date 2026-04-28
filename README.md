# Yokogawa Marketplace
This is the backend for the marketplace for battery recycling.

This project is a fully autonomous, cloud-native bidding marketplace powered by collaborative multi-agent LLMs and the Model Communication Protocol (MCP). It is designed to enable enterprises to deploy, manage, and scale AI agents that can independently participate in complex industrial workflows.

The platform supports the complete transaction lifecycle—starting from RFQ (Request for Quotation) generation and intelligent vendor discovery, to multi-agent negotiation, contract finalization, and fulfillment tracking. Each stage is handled by specialized AI agents that can reason, communicate, and make context-aware decisions with minimal human intervention.

At its core, the system facilitates dynamic, real-time interactions between multiple agents representing different stakeholders such as manufacturers, suppliers, logistics providers, and service partners. These agents collaborate through a structured communication layer (MCP), ensuring reliable, schema-driven message exchange and coordinated decision-making across distributed workflows.

Built on scalable cloud infrastructure, the platform is capable of handling concurrent agent operations with low latency, making it suitable for enterprise-grade deployments. By automating traditionally manual and time-intensive processes, the system significantly accelerates deal cycles, improves operational efficiency, and reduces friction in industrial transactions.

Overall, this project introduces a new paradigm of “Agent-as-a-Service”, where organizations can host and orchestrate intelligent agents to autonomously execute and optimize end-to-end business processes within industrial ecosystems.

# Service bus usage design:

One queue for holding all messages.
There will N topics in this queue, one for each user.
There will be two subscribers for each topic, which will be created when we register a new user.

One subscriber is for the human: with this, we will push notifications to the front end.
One subscriber is for the agent: the agent will get messages, and respond on behalf of the human, if
   the human has given permission. If the bot should not get certain messages, we can use filters.

All agents will be allowed to send messages to each other. The receiving user's id has to be known, and the topic name of the dst will be topic_{dst_user_id}.

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
