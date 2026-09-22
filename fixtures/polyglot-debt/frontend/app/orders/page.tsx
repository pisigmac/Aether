import { fetchOrders } from "../../lib/api";

export default async function OrdersPage() {
  const orders = await fetchOrders();
  return (
    <main>
      <h1>Orders</h1>
      <ul>
        {orders.map((order) => (
          <li key={order.id}>
            #{order.id} {order.status} {order.total} {JSON.stringify(order.metadata)}
          </li>
        ))}
      </ul>
    </main>
  );
}
