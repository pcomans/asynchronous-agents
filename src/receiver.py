#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import threading
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from agents import Agent, Runner, function_tool
from rich.console import Console
from rich.panel import Panel
from consumers import ReconnectingTopicConsumer

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
             '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
console = Console()

# Available topics that agents can subscribe to
AVAILABLE_TOPICS = [
    {
        "name": "jokes",
        "description": "A topic for receiving and generating jokes",
        "binding_key": "jokes.*"
    },
    {
        "name": "poems",
        "description": "A topic for receiving and generating poems",
        "binding_key": "poems.*"
    },
    {
        "name": "limericks",
        "description": "A topic for receiving and generating limericks",
        "binding_key": "limericks.*"
    }
]

AGENT_REGISTRY = {}

@function_tool
def subscribe_to_topic(agent_id: str, topic_name: str) -> str:
    """Tool for subscribing an agent to a topic"""
    if agent_id not in AGENT_REGISTRY:
        return f"Error: Agent {agent_id} not found in registry"
        
    topic = next((t for t in AVAILABLE_TOPICS if t['name'] == topic_name), None)
    if not topic:
        print(f"Topic {topic_name} not found")
        return
    
    binding_key = topic['binding_key']
    amqp_url = 'amqp://guest:guest@localhost:5672/%2F'
    
    consumer = ReconnectingTopicConsumer(
        amqp_url, 
        agent_id, 
        binding_key, 
        topic_name,
        AGENT_REGISTRY
    )
    threading.Thread(target=consumer.run, daemon=True).start()
    
    print(f"Subscribed to {topic_name} for agent {agent_id}")
    return f"Subscribed to {topic_name} for agent {agent_id}"

@function_tool
def list_topics() -> str:
    """Tool for listing all available topics"""
    return "\n".join([f"{t['name']}: {t['description']}" for t in AVAILABLE_TOPICS])

def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    load_dotenv()

    console.print(Panel(
        f"Starting RabbitMQ Topic Consumer",
        title="[bold green]RabbitMQ Topic Consumer[/bold green]",
        width=console.width,
        style="cyan"
    ))

    agent_tools = [subscribe_to_topic, list_topics]

    poetry_agent = Agent(
        name="poetry_agent",
        instructions="You are an agent that writes poetry. Your ID is poetry_agent.",
        tools=agent_tools
    )
    AGENT_REGISTRY['poetry_agent'] = poetry_agent

    joking_agent = Agent(
        name="joking_agent",
        instructions="You are an agent that writes jokes. Your ID is joking_agent.",
        tools=agent_tools
    )
    AGENT_REGISTRY['joking_agent'] = joking_agent

    poetry_result = Runner.run_sync(poetry_agent, "Please subscribe to the appropriate topics for your role.")
    console.print(Panel(
        poetry_result.final_output,
        title="[bold green]Poetry Agent Subscription[/bold green]",
        width=console.width,
        style="cyan"
    ))

    joking_result = Runner.run_sync(joking_agent, "Please subscribe to the appropriate topics for your role.")
    console.print(Panel(
        joking_result.final_output,
        title="[bold green]Joking Agent Subscription[/bold green]",
        width=console.width,
        style="cyan"
    ))

    try:
        console.print(Panel(
            "Waiting for messages. Press CTRL+C to exit.",
            title="[bold yellow]Status[/bold yellow]",
            width=console.width,
            style="yellow"
        ))
        threading.Event().wait()
    except KeyboardInterrupt:
        console.print(Panel(
            "Shutting down...",
            title="[bold red]Shutdown[/bold red]",
            width=console.width,
            style="red"
        ))

if __name__ == '__main__':
    main()
