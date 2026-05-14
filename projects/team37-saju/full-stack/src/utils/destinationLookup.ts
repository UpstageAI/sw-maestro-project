import { DESTINATIONS, type EnrichedDestination } from '../mocks/destinations';

export function findEnrichedDestinationById(
  id: string,
): EnrichedDestination | undefined {
  return DESTINATIONS.find((d) => d.id === id);
}
