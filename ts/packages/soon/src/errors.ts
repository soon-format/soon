/** Exception hierarchy for @soon-format/soon. */

export class SoonError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = new.target.name;
  }
}

export class SoonEncodeError extends SoonError {}

export class SoonDecodeError extends SoonError {}
