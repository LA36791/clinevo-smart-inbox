import { TestBed } from '@angular/core/testing';
import { Inbox } from './inbox';

describe('Inbox', () => {
  let service: Inbox;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Inbox);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
