# 10. Diagrams and Visuals

## 10.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       Client Application                     │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Router                          │
└───────┬─────────────────────┬────────────────────┬──────────┘
        │                     │                    │
        ▼                     ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Gemini API   │    │     Ollama    │    │  Transformers │
│  (External)    │    │  (Local API)  │    │ (Local Lib)   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                    │
        └─────────────────────┼────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Availability Monitoring System                │
└─────────────────────────────────────────────────────────────┘
```

## 10.2 Service Monitoring Flowchart

```
┌─────────────┐                 ┌────────────────┐
│  Start      │                 │ Check Interval │
│ Application ├────────────────►│   Reached?     │
└─────────────┘                 └────────┬───────┘
                                         │
                                         ▼
┌─────────────┐                 ┌────────────────┐
│   Update    │                 │ Check Service  │
│   Cache     │◄────────────────┤ Availability   │
└─────┬───────┘                 └────────────────┘
      │
      ▼
┌─────────────┐                 ┌────────────────┐
│  Status     │     Yes         │ Status         │
│  Changed?   ├────────────────►│ Change Event   │
└─────┬───────┘                 └────────┬───────┘
      │                                  │
      │ No                               ▼
      │                         ┌────────────────┐
      │                         │ Update Logs &  │
      │                         │ Send Alerts    │
      │                         └────────────────┘
      ▼
┌─────────────┐
│ Wait for    │
│ Next Check  │
└─────────────┘
```

## 10.3 Failover Process Diagram

```
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│ Request       │         │ Service        │         │ Service       │
│ Received      ├────────►│ Available?     ├─Yes────►│ Rate-Limited? │
└───────────────┘         └───────┬───────┘         └───────┬───────┘
                                  │                          │
                                  │ No                       │ No
                                  ▼                          ▼
                          ┌───────────────┐         ┌───────────────┐
                          │ Try Next      │         │ Process with  │
                          │ Service       │         │ Primary Service│
                          └───────┬───────┘         └───────────────┘
                                  │
                                  │
                                  ▼
                          ┌───────────────┐         ┌───────────────┐
                          │ Any Service   │         │ Return Error  │
                          │ Available?    ├─No─────►│ Use Client    │
                          └───────┬───────┘         │ Fallback      │
                                  │                 └───────────────┘
                                  │ Yes
                                  ▼
                          ┌───────────────┐
                          │ Process with  │
                          │ Available     │
                          │ Service       │
                          └───────────────┘
```

## 10.4 Rate Limit Monitoring Diagram

```
┌───────────────┐         ┌───────────────┐
│ Track API     │         │ Reset         │
│ Request       ├────────►│ Period        │
└───────┬───────┘         │ Elapsed?      │
        │                 └───────┬───────┘
        │                         │
        │                         │ Yes
        │                         ▼
        │                 ┌───────────────┐
        │                 │ Reset         │
        │                 │ Counters      │
        │                 └───────┬───────┘
        │                         │
        ▼                         │
┌───────────────┐                 │
│ Increment     │◄────────────────┘
│ Counters      │
└───────┬───────┘
        │
        ▼
┌───────────────┐         ┌───────────────┐
│ Approaching   │         │ Log Warning    │
│ Limit?        ├─Yes────►│ Prepare       │
└───────┬───────┘         │ Fallback      │
        │                 └───────────────┘
        │ No
        ▼
┌───────────────┐
│ Continue      │
│ Normal        │
│ Operation     │
└───────────────┘
```

## 10.5 Recovery Detection Process

```
┌───────────────┐         ┌───────────────┐
│ Service       │         │ Periodic      │
│ Unavailable   ├────────►│ Health        │
└───────────────┘         │ Check         │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌───────────────┐         ┌───────────────┐
                          │ Service       │         │ Continue      │
                          │ Recovered?    ├─No─────►│ Using         │
                          └───────┬───────┘         │ Fallback      │
                                  │                 └───────────────┘
                                  │ Yes
                                  ▼
                          ┌───────────────┐
                          │ Log Recovery  │
                          │ Update Status │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ Resume Using  │
                          │ Preferred     │
                          │ Service       │
                          └───────────────┘
```

## 10.6 User Experience Flow

```
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│ User          │         │ Frontend      │         │ API Request   │
│ Submits       ├────────►│ Processes     ├────────►│ to Server     │
│ Query         │         │ Input         │         │               │
└───────────────┘         └───────────────┘         └───────┬───────┘
                                                            │
        ┌───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│ Server        │    No   │ Client-side   │         │ Show Error    │
│ Available?    ├────────►│ Fallback      ├────────►│ Message with  │
└───────┬───────┘         │ Activated     │         │ Limited Mode  │
        │                 └───────────────┘         └───────────────┘
        │ Yes
        ▼
┌───────────────┐         ┌───────────────┐
│ Service       │         │ Notify User   │
│ Using         ├────────►│ of Service    │
│ Fallback?     │   Yes   │ Limitations   │
└───────┬───────┘         └───────────────┘
        │
        │ No
        ▼
┌───────────────┐
│ Normal        │
│ Response      │
│ Processing    │
└───────────────┘
```