export interface Sample {
  name: string;
  description: string;
  data: unknown;
}

export const SAMPLES: Sample[] = [
  {
    name: "Flat table",
    description: "100 uniform employee rows",
    data: (() => {
      const names = ["Ada", "Linus", "Grace", "Edsger", "Alan", "Barbara", "Ken", "Dennis", "Radia", "Anita"];
      const roles = ["admin", "dev", "ops", "design", "pm"];
      let seed = 2;
      const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
      return {
        employees: Array.from({ length: 100 }, (_, i) => ({
          id: i + 1,
          name: names[Math.floor(rnd() * names.length)],
          role: roles[Math.floor(rnd() * roles.length)],
          salary: Math.floor(rnd() * 200 + 100) * 500,
          remote: rnd() < 0.5,
        })),
      };
    })(),
  },
  {
    name: "Nested orders",
    description: "10 orders with nested customers & items",
    data: (() => {
      const names = ["Ada", "Linus", "Grace", "Edsger", "Alan"];
      const cities = [["Boulder", "80301"], ["Helsinki", "00100"], ["Arlington", "22201"]];
      let seed = 4;
      const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
      return {
        orders: Array.from({ length: 10 }, (_, i) => {
          const [city, zip] = cities[Math.floor(rnd() * cities.length)];
          return {
            id: i + 1,
            status: ["shipped", "pending", "cancelled"][Math.floor(rnd() * 3)],
            customer: {
              name: names[Math.floor(rnd() * names.length)],
              tier: ["gold", "silver", "bronze"][Math.floor(rnd() * 3)],
              address: { city, zip, country: "US" },
            },
            items: Array.from({ length: Math.floor(rnd() * 3) + 1 }, () => ({
              sku: `SKU-${Math.floor(rnd() * 98) + 1}`,
              qty: Math.floor(rnd() * 4) + 1,
              price: Math.round(rnd() * 3800 + 200) / 100,
            })),
          };
        }),
      };
    })(),
  },
  {
    name: "Deeply nested",
    description: "Org with teams, projects, tasks (depth 5)",
    data: {
      org: {
        name: "acme",
        teams: [
          {
            team: "team-0",
            lead: "Ada",
            projects: [
              {
                key: "PRJ-00",
                budget: 120000,
                tasks: [
                  { id: 1, title: "task 0", done: false, assignee: { name: "Grace", role: "dev" } },
                  { id: 2, title: "task 1", done: true, assignee: { name: "Linus", role: "ops" } },
                ],
              },
              {
                key: "PRJ-01",
                budget: 250000,
                tasks: [
                  { id: 3, title: "task 0", done: false, assignee: { name: "Ada", role: "pm" } },
                ],
              },
            ],
          },
          {
            team: "team-1",
            lead: "Edsger",
            projects: [
              {
                key: "PRJ-10",
                budget: 80000,
                tasks: [
                  { id: 4, title: "task 0", done: true, assignee: { name: "Ken", role: "admin" } },
                  { id: 5, title: "task 1", done: false, assignee: { name: "Barbara", role: "design" } },
                  { id: 6, title: "task 2", done: true, assignee: { name: "Dennis", role: "dev" } },
                ],
              },
            ],
          },
        ],
      },
    },
  },
  {
    name: "Simple object",
    description: "Flat config (6 keys)",
    data: {
      app: "checkout-service",
      version: "2.14.1",
      debug: false,
      port: 8080,
      timeoutMs: 30000,
      region: "eu-central-1",
    },
  },
];
