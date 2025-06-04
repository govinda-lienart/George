# George AI Hotel Receptionist Pipeline

This diagram shows the complete architecture and flow of the George AI system.

```mermaid
flowchart TD
    Start([User Types Message]) --> Router{Router LLM<br/>GPT-3.5-turbo}
    
    Router -->|Availability & Prices| SQL[SQL Tool]
    Router -->|Hotel Info & Policies| Vector[Vector Tool] 
    Router -->|Booking Requests| Booking[Booking Tool]
    Router -->|General Chat| Chat[Chat Tool]
    
    SQL --> Database[(MySQL Database)]
    Vector --> VectorStore[(Pinecone VectorDB)]
    Booking --> BookingUI[Show Booking Form]
    Chat --> StaticFiles[Load hotel_facts.txt]
    
    Database --> SQLResponse[SQL Response]
    VectorStore --> VectorResponse[Vector Response]
    BookingUI --> BookingComplete{Booking Completed?}
    StaticFiles --> ChatResponse[Chat Response]
    
    BookingComplete -->|Yes| BookingDB[Store in MySQL & Send Email]
    BookingComplete -->|No| FormActive[Form Stays Active]
    
    SQLResponse --> Memory[Save to Memory]
    VectorResponse --> Memory
    ChatResponse --> Memory
    BookingDB --> Memory
    
    Memory --> Display[Display in Chat UI]