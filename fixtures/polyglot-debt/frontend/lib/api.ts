export type Order = {
  id: number;
  user_id: number;
  total: number;
  status: string;
  metadata: Record<string, unknown>;
};

export async function fetchOrders(): Promise<Order[]> {
  const res = await fetch("/orders");
  if (!res.ok) {
    throw new Error("failed to load orders");
  }
  return res.json();
}

export async function fetchUsers() {
  const res = await fetch("/users");
  return res.json();
}
