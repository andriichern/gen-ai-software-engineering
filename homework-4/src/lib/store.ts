import { Order } from "./types";

class OrderStore {
  private orders: Map<string, Order> = new Map();
  private static instance: OrderStore;

  private constructor() {}

  static getInstance(): OrderStore {
    if (!OrderStore.instance) {
      OrderStore.instance = new OrderStore();
    }
    return OrderStore.instance;
  }

  create(order: Order): Order {
    this.orders.set(order.id, order);
    return order;
  }

  getById(id: string): Order | undefined {
    return this.orders.get(id);
  }

  getAll(): Order[] {
    return Array.from(this.orders.values());
  }

  update(id: string, updates: Partial<Order>): Order | undefined {
    const order = this.orders.get(id);
    if (!order) return undefined;

    const updated = { ...order, ...updates };
    this.orders.set(id, updated);
    return updated;
  }

  delete(id: string): boolean {
    return this.orders.delete(id);
  }

  clear(): void {
    this.orders.clear();
  }
}

export default OrderStore.getInstance();
