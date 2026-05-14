import type { Agent, DiscussionRound as DiscussionRoundType } from '@/types';
import { SectionTitle } from '@/components/common';
import { UserInputBanner } from './UserInputBanner';
import { DiscussionRound } from './DiscussionRound';
import { Button } from '@/components/ui/button';
import { Info } from 'lucide-react';
import { consultationContent } from '@/content';

interface DiscussionPhaseProps {
  userInput: string;
  agents: Agent[];
  rounds: DiscussionRoundType[];
  currentRound: number;
  onEditInput?: () => void;
}

export function DiscussionPhase({ userInput, agents, rounds, currentRound, onEditInput }: DiscussionPhaseProps) {
  const visibleRounds = rounds.filter((r) => r.roundNumber === currentRound);

  return (
    <div className="flex flex-col gap-6">
      <UserInputBanner userInput={userInput} onEdit={onEditInput} />
      <SectionTitle
        title={`${currentRound + 1}라운드 - ${currentRound === 1 ? consultationContent.round2.title : consultationContent.round3.title}`}
        subtitle={currentRound === 1 ? consultationContent.round2.description : consultationContent.round3.description}
        action={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs">
            라운드 안내
            <Info className="size-3.5" />
          </Button>
        }
      />
      <div className="flex flex-col gap-8">
        {visibleRounds.map((round) => (
          <DiscussionRound key={round.roundNumber} round={round} agents={agents} />
        ))}
      </div>
    </div>
  );
}
